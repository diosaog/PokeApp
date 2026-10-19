"""Project the existing database-validated E/I evidence without granting rewards."""

import json

from app.repositories.errors import PersistenceError
from app.save_parser.models import NativeGameProgress, ObservedProgress, progress_layout


def progress_read(row):
    # api.__init__ loads routes. Import DTOs after this module is initialized so
    # native/local validators can also call the projection without boot order.
    from app.api.progress_models import BadgeRegionRead, ProgressRead

    if row.get("native_progress") is not None:
        native = NativeGameProgress.model_validate_json(
            json.dumps(row["native_progress"])
        )
        game = row["game"]
        if (
            row["observed_at"] is None
            or (native.model == "gym_badges" and game not in {"X", "Y", "OR", "AS"})
            or (
                native.model == "island_challenge"
                and game not in {"SN", "MN", "US", "UM"}
            )
        ):
            raise PersistenceError("Invalid native progress scope")
        region = "kalos" if game in {"X", "Y"} else "hoenn"
        return ProgressRead(
            state="observed",
            game=game,
            observed_at=row["observed_at"],
            native_model=native.model,
            badges_count=sum(native.badge_flags)
            if native.badge_flags is not None
            else None,
            primary_region=region if native.badge_flags is not None else None,
            regions=[
                BadgeRegionRead(
                    region=region,
                    earned_badges=[
                        i for i, flag in enumerate(native.badge_flags, 1) if flag
                    ],
                )
            ]
            if native.badge_flags is not None
            else None,
            champion_defeated=native.champion_defeated,
            league_access=native.league_access,
            league_visited=native.league_visited,
            league_fly_unlocked=native.league_fly_unlocked,
            hall_of_fame_entered=native.hall_of_fame_entered,
            completed_islands=[
                island
                for island, earned in zip(
                    ("melemele", "akala", "ulaula", "poni"), native.island_stamp_flags
                )
                if earned
            ]
            if native.island_stamp_flags is not None
            else None,
            island_challenge_completed=native.island_challenge_completed,
            reward_state="pending_validation"
            if native.model == "gym_badges"
            else "pending_policy",
        )
    value = row["progress"]
    if value is None:
        if row["game"] is not None or row["observed_at"] is not None:
            raise PersistenceError("Invalid unknown progress")
        return ProgressRead()
    # The transport supplies JSON arrays; keep the parser's strict scalar checks.
    evidence = ObservedProgress.model_validate_json(json.dumps(value))
    layout = progress_layout(row["game"])
    if (
        layout is None
        or tuple(r.region for r in evidence.regions) != layout[1]
        or row["observed_at"] is None
    ):
        raise PersistenceError("Invalid progress scope")
    regions = [
        BadgeRegionRead(
            region=r.region,
            earned_badges=[i for i, earned in enumerate(r.badge_flags, 1) if earned],
        )
        for r in evidence.regions
    ]
    return ProgressRead(
        state="observed",
        game=row["game"],
        observed_at=row["observed_at"],
        badges_count=sum(len(r.earned_badges) for r in regions),
        primary_region=evidence.primary_region,
        regions=regions,
        champion_defeated=evidence.champion_defeated,
    )
