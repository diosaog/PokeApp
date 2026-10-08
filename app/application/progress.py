"""Project the existing database-validated E/I evidence without granting rewards."""

import json

from app.repositories.errors import PersistenceError
from app.save_parser.models import ObservedProgress, progress_layout


def progress_read(row):
    # api.__init__ loads routes. Import DTOs after this module is initialized so
    # native/local validators can also call the projection without boot order.
    from app.api.progress_models import BadgeRegionRead, ProgressRead

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
