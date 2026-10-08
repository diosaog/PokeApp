"""A narrower, single-trainer public view of H's competitive Team Lock reader."""

from app.api.scouting_models import ScoutingRead
from app.api.team_preview_models import TeamPreviewQuery
from app.application.team_preview import team_preview


def scouting(repository, season_id, viewer_trainer_id, selection):
    preview = team_preview(
        repository,
        season_id,
        viewer_trainer_id,
        TeamPreviewQuery(mode="spectator", trainer_id=selection.trainer_id),
        single_public=True,
    )
    ids = [str(t.trainer_id) for t in preview.trainers]
    selected = (
        str(selection.trainer_id)
        if selection.trainer_id
        else (viewer_trainer_id if viewer_trainer_id in ids else next(iter(ids), None))
    )
    lock = preview.teams[0].lock if preview.teams else None
    # Revalidate through the deliberately smaller DTO, including nested moves.
    # PP/shiny/timestamps are not added to K's approved competitive field list.
    return ScoutingRead(
        season=preview.season,
        day=preview.day,
        trainers=preview.trainers,
        trainer_id=selected,
        team=[p.model_dump() for p in lock.team] if lock is not None else None,
        team_lock_status=lock.timing_status if lock is not None else "pending",
    )
