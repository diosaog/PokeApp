"""Bounded current-day competitive preview, independent of scheduled matches."""

from app.api.team_preview_models import TeamPreviewRead
from app.application.frontend_reads import FrontendReads
from app.repositories.errors import NotFoundError, PersistenceError


def team_preview(
    repository, season_id, viewer_trainer_id, selection, *, single_public=False
):
    # Internal public-only reuse for scouting, never a client authority flag.
    if single_public and (selection.mode != "spectator" or selection.second_trainer_id):
        raise ValueError("Single public projection requires spectator selection")
    reads = FrontendReads(repository)
    season = reads.season(season_id)
    names = {str(t.id): t.display_name for t in reads.trainers()}
    roster = reads.rows(
        "public_season_players", "trainer_id,status", season_id=season_id
    )
    by_trainer = {p["trainer_id"]: p for p in roster}
    if len(by_trainer) != len(roster):
        raise PersistenceError("Ambiguous preview roster")
    trainers = [
        dict(
            trainer_id=p["trainer_id"],
            status=p["status"],
            display_name=names.get(p["trainer_id"], "Entrenador no disponible"),
        )
        for p in roster
    ]
    first = (
        str(selection.trainer_id)
        if selection.trainer_id
        else (
            viewer_trainer_id
            if viewer_trainer_id in by_trainer
            else next(iter(by_trainer), None)
        )
    )
    second = str(selection.second_trainer_id) if selection.second_trainer_id else None
    if not single_public and selection.mode == "spectator" and second is None:
        second = next((tid for tid in by_trainer if tid != first), None)
    selected = [tid for tid in (first, second) if tid is not None]
    if any(tid not in by_trainer for tid in selected):
        raise NotFoundError("Preview participant not found")
    day_id = season["current_matchday_id"]
    day = None
    if day_id:
        days = reads.rows(
            "public_matchdays", "id,number,status", id=day_id, season_id=season_id
        )
        if len(days) != 1:
            raise PersistenceError("Preview day unavailable")
        day = days[0]
    teams = []
    if day:
        # One bounded public query for the day; no per-player read loop. Private
        # columns are never selected here, including when the viewer is selected.
        public = reads.rows(
            "public_team_locks",
            "trainer_id,matchday_id,locked_at,is_late,public_team_snapshot",
            season_id=season_id,
            matchday_id=day_id,
        )
        locks = {r["trainer_id"]: r for r in public}
        if len(locks) != len(public):
            raise PersistenceError("Ambiguous preview locks")
        for tid in selected:
            own = selection.mode == "battle" and tid == viewer_trainer_id
            source = locks.get(tid)
            key = "public_team_snapshot"
            if own:
                # Only the server-authenticated owner can reach this SELECT.
                private = reads.rows(
                    "team_locks",
                    "trainer_id,matchday_id,locked_at,is_late,private_team_snapshot",
                    season_id=season_id,
                    matchday_id=day_id,
                    trainer_id=viewer_trainer_id,
                )
                if len(private) > 1:
                    raise PersistenceError("Ambiguous own lock")
                source = private[0] if private else None
                key = "private_team_snapshot"
            lock = None
            if source is not None:
                if source["trainer_id"] != tid or source["matchday_id"] != day_id:
                    raise PersistenceError("Invalid preview lock scope")
                team = source[key]
                if not isinstance(team, list) or any(
                    not isinstance(p, dict)
                    or not isinstance(p.get("species"), str)
                    or not p["species"].strip()
                    for p in team
                ):
                    raise PersistenceError("Invalid preview snapshot")
                lock = dict(
                    locked_at=source["locked_at"], is_late=source["is_late"], team=team
                )
            teams.append(
                dict(trainer_id=tid, visibility="self" if own else "public", lock=lock)
            )
    return TeamPreviewRead(
        season=season, day=day, trainers=trainers, mode=selection.mode, teams=teams
    )
