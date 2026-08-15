from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.liga.permissions import require_league_admin


SEASON_DISCARD_DECISION = "discard"
SEASON_DISCARD_CONFIRMATION = "DESCARTAR"


def discard_active_season(
    *,
    admin_user: str | None,
    decision: str,
    confirmation: str,
    wipe_fn: Callable[[], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Danger-zone action for intentionally discarding the active season."""

    require_league_admin(admin_user)
    if str(decision or "").strip().lower() != SEASON_DISCARD_DECISION:
        raise ValueError("Elige explicitamente descartar temporada antes de reiniciar.")
    if str(confirmation or "").strip() != SEASON_DISCARD_CONFIRMATION:
        raise ValueError("La confirmacion textual no coincide.")
    if wipe_fn is None:
        from app.season.archive import mark_season_discarded

        runner = lambda: mark_season_discarded(admin_user=admin_user)
    else:
        runner = wipe_fn
    report = runner()
    if not isinstance(report, dict):
        return {"ok": False, "errors": ["La accion de descarte no devolvio un informe valido."]}
    return report
