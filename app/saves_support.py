from __future__ import annotations

from datetime import datetime
import html as _html
from pathlib import Path

from app.liga.ranking import clear_ranking_caches
from app.tienda.money import clear_money_caches
from storage import (
    get_current_save_for_user,
    list_saves_by_user,
    load_save_bytes,
    set_current_save_for_user,
)
from utils import ensure_user_dir, ts_name

SAVES_PAGE_CSS = """
<style>
.saves-hero {
  position:relative;
  overflow:hidden;
  padding:18px 18px 16px;
  margin-bottom:14px;
  border:1px solid var(--bw2-edge);
  background:
    linear-gradient(120deg, rgba(110,168,255,0.24), transparent 36%),
    linear-gradient(180deg, var(--bw2-panel-2), var(--bw2-panel));
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 30px rgba(0,0,0,0.2);
}
.saves-kicker {
  color:var(--accent-soft);
  font-family:var(--font-pixel);
  font-size:10px;
  text-transform:uppercase;
}
.saves-title {
  margin-top:10px;
  color:#fff;
  font-family:var(--font-pixel);
  font-size:22px;
  line-height:1.22;
  text-transform:uppercase;
}
.saves-subtitle {
  margin-top:8px;
  max-width:880px;
  color:var(--bw2-text-soft);
  font-size:22px;
  line-height:1.12;
}
.bill-divider,
.saves-divider {
  height:2px;
  background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%);
  margin:12px 0 16px;
}
.bill-chip,
.saves-section-title {
  display:inline-block;
  background:linear-gradient(180deg,var(--bw2-panel-3) 0%, var(--bw2-panel) 100%);
  border:1px solid var(--bw2-edge);
  border-radius:0;
  padding:8px 10px;
  color:var(--bw2-text);
  font-family:var(--font-pixel);
  font-size:10px;
  font-weight:700;
  text-transform:uppercase;
}
.bill-chip b,
.saves-section-title b { color:#fff; }
.saves-status-grid {
  display:grid;
  grid-template-columns:repeat(4, minmax(0, 1fr));
  gap:10px;
  margin:12px 0 16px;
}
.saves-stat {
  min-height:96px;
  padding:12px;
  border:1px solid rgba(216,223,232,0.2);
  background:
    linear-gradient(90deg, rgba(255,255,255,0.06), transparent 58%),
    linear-gradient(180deg, var(--bw2-screen-2), var(--bw2-screen));
  box-shadow:inset 0 1px 0 rgba(255,255,255,0.06);
}
.saves-stat-label {
  color:var(--bw2-text-dim);
  font-family:var(--font-pixel);
  font-size:9px;
  text-transform:uppercase;
}
.saves-stat-value {
  margin-top:10px;
  color:#fff;
  font-family:var(--font-pixel);
  font-size:14px;
  line-height:1.22;
  overflow-wrap:anywhere;
}
.saves-stat-detail {
  margin-top:7px;
  color:var(--bw2-text-soft);
  font-size:18px;
  line-height:1.08;
  overflow-wrap:anywhere;
}
.bill-save-meta,
.saves-current-card,
.saves-history-card,
.saves-admin-panel {
  margin-top:8px;
  background:
    linear-gradient(90deg, rgba(255,255,255,0.05), transparent 60%),
    linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
  border:1px solid var(--bw2-edge);
  border-radius:0;
  padding:12px;
  color:var(--bw2-text-soft);
  font-family:var(--font-ui);
  font-size:18px;
  font-weight:400;
  line-height:1.18;
  letter-spacing:0;
}
.saves-current-card {
  border-left:4px solid var(--accent);
}
.saves-history-card.is-current {
  border-color:var(--accent-soft);
  box-shadow:inset 4px 0 0 var(--accent);
}
.saves-card-top {
  display:flex;
  justify-content:space-between;
  gap:12px;
  align-items:flex-start;
}
.saves-card-title {
  color:#fff;
  font-family:var(--font-pixel);
  font-size:12px;
  line-height:1.24;
  text-transform:uppercase;
  overflow-wrap:anywhere;
}
.saves-card-badge {
  flex:0 0 auto;
  padding:4px 7px;
  border:1px solid rgba(216,223,232,0.22);
  background:linear-gradient(180deg, var(--bw2-panel-3), var(--bw2-panel));
  color:var(--bw2-text);
  font-family:var(--font-pixel);
  font-size:8px;
  text-transform:uppercase;
}
.saves-card-badge.is-current {
  background:linear-gradient(180deg, var(--accent), var(--accent-dark));
  color:#fff;
  border-color:var(--bw2-edge-strong);
}
.saves-card-meta {
  margin-top:10px;
  display:grid;
  grid-template-columns:repeat(4, minmax(0, 1fr));
  gap:8px;
}
.saves-meta-cell {
  min-height:52px;
  padding:8px;
  border:1px solid rgba(216,223,232,0.12);
  background:rgba(0,0,0,0.14);
}
.saves-meta-label {
  color:var(--bw2-text-dim);
  font-family:var(--font-pixel);
  font-size:8px;
  text-transform:uppercase;
}
.saves-meta-value {
  margin-top:5px;
  color:var(--bw2-text-soft);
  font-size:17px;
  line-height:1.02;
  overflow-wrap:anywhere;
}
.bill-save-meta b { color:#fff; font-weight:700; font-family:var(--font-pixel); font-size:10px; }
.saves-admin-panel {
  border-left:4px solid var(--bw2-warn);
}
.saves-admin-title {
  color:#fff;
  font-family:var(--font-pixel);
  font-size:12px;
  text-transform:uppercase;
}
.saves-admin-body {
  margin-top:8px;
  color:var(--bw2-text-soft);
  font-size:18px;
  line-height:1.1;
}
div[data-testid="stFileUploaderDropzone"] {
  background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%) !important;
  border:1px dashed var(--bw2-edge) !important;
  border-radius:0 !important;
  min-height:132px !important;
}
div[data-testid="stFileUploaderDropzone"] * {
  font-family:var(--font-ui) !important;
  font-weight:400 !important;
  color:var(--bw2-text-soft) !important;
}
div[data-testid="stAlert"] {
  border:1px solid var(--bw2-edge) !important;
  border-radius:0 !important;
}
div[data-testid="stAlert"] * {
  font-family:var(--font-ui) !important;
  font-weight:400 !important;
}
details[data-testid="stExpander"] > summary {
  font-family:var(--font-pixel) !important;
  font-weight:700 !important;
  font-size:10px !important;
}
@media (max-width: 980px) {
  .saves-status-grid { grid-template-columns:repeat(2, minmax(0, 1fr)); }
  .saves-card-meta { grid-template-columns:repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 640px) {
  .saves-status-grid,
  .saves-card-meta { grid-template-columns:1fr; }
  .saves-title { font-size:18px; }
  .saves-subtitle { font-size:20px; }
}
</style>
"""


def _cell(label: str, value: str) -> str:
    return (
        "<div class='saves-meta-cell'>"
        f"<div class='saves-meta-label'>{_html.escape(label)}</div>"
        f"<div class='saves-meta-value'>{_html.escape(value)}</div>"
        "</div>"
    )


def _stat(label: str, value: str, detail: str) -> str:
    return (
        "<div class='saves-stat'>"
        f"<div class='saves-stat-label'>{_html.escape(label)}</div>"
        f"<div class='saves-stat-value'>{_html.escape(value)}</div>"
        f"<div class='saves-stat-detail'>{_html.escape(detail)}</div>"
        "</div>"
    )


def save_timestamp_label(ts: object) -> str:
    try:
        stamp = int(ts or 0)
    except Exception:
        stamp = 0
    if stamp <= 0:
        return "Sin fecha"
    return datetime.fromtimestamp(stamp).strftime("%d/%m/%Y %H:%M")


def save_row_id(row: tuple | None) -> int | None:
    if not row:
        return None
    try:
        return int(row[0])
    except Exception:
        return None


def save_row_filename(row: tuple | None) -> str:
    if not row:
        return ""
    return str(row[1] or "")


def save_file_label(row: tuple | None) -> str:
    if not row:
        return "Sin save"
    return str(row[2] or row[1] or "Save sin nombre")


def save_owner_label(row: tuple | None) -> str:
    if not row:
        return "-"
    return str(row[4] or "-")


def save_sha_label(row: tuple | None) -> str:
    if not row:
        return "-"
    raw = str(row[3] or "")
    return raw[:8] if raw else "-"


def saves_summary_html(
    current_user: str | None,
    current: tuple | None,
    history: list[tuple],
    *,
    retired: bool = False,
) -> str:
    latest = history[0] if history else None
    current_detail = save_timestamp_label(current[5]) if current else "Subida pendiente"
    latest_detail = save_timestamp_label(latest[5]) if latest else "Sin historial"
    mode = "Solo consulta" if retired else "Subida activa"
    user = str(current_user or "-")
    return (
        "<div class='saves-status-grid'>"
        + _stat("Entrenador", user, mode)
        + _stat("Save actual", save_file_label(current), current_detail)
        + _stat("Ultima subida", save_file_label(latest), latest_detail)
        + _stat("Historial", f"{len(history)} saves", "Ultimos registros")
        + "</div>"
    )


def save_card_html(row: tuple, *, current_id: int | None = None) -> str:
    id_ = save_row_id(row)
    current = id_ is not None and current_id is not None and id_ == current_id
    badge = "Actual" if current else "Archivado"
    class_name = "saves-history-card is-current" if current else "saves-history-card"
    return (
        f"<div class='{class_name}'>"
        "<div class='saves-card-top'>"
        f"<div class='saves-card-title'>[{_html.escape(str(id_ or '-'))}] {_html.escape(save_file_label(row))}</div>"
        f"<div class='saves-card-badge{' is-current' if current else ''}'>{_html.escape(badge)}</div>"
        "</div>"
        "<div class='saves-card-meta'>"
        + _cell("Subido por", save_owner_label(row))
        + _cell("Fecha", save_timestamp_label(row[5]))
        + _cell("SHA", save_sha_label(row))
        + _cell("Archivo", save_row_filename(row) or "-")
        + "</div>"
        "</div>"
    )


def current_save_meta_html(row: tuple) -> str:
    return (
        "<div class='saves-current-card'>"
        "<div class='saves-card-top'>"
        f"<div class='saves-card-title'>{_html.escape(save_file_label(row))}</div>"
        "<div class='saves-card-badge is-current'>Actual</div>"
        "</div>"
        "<div class='saves-card-meta'>"
        + _cell("ID", str(save_row_id(row) or "-"))
        + _cell("Subido por", save_owner_label(row))
        + _cell("Fecha", save_timestamp_label(row[5]))
        + _cell("SHA", save_sha_label(row))
        + "</div>"
        "</div>"
    )


def clear_save_related_caches() -> None:
    clear_money_caches()
    clear_ranking_caches()
    try:
        import storage as _storage

        for cache_name in ("_fetch_save_by_id", "list_saves", "list_saves_by_user"):
            cache_fn = getattr(_storage, cache_name, None)
            clear_fn = getattr(cache_fn, "clear", None)
            if callable(clear_fn):
                clear_fn()
    except Exception:
        pass
    try:
        from app.entrenadores.snapshot import clear_trainer_snapshot_runtime_caches

        clear_trainer_snapshot_runtime_caches()
    except Exception:
        pass
    try:
        import utils as _utils

        cache_fn = getattr(_utils, "_list_user_saves_cached", None)
        if cache_fn is not None:
            cache_fn.clear()
    except Exception:
        pass


def refresh_save_snapshot(current_user: str | None) -> None:
    if not current_user:
        return
    try:
        from app.entrenadores.snapshot import refresh_trainer_snapshot

        refresh_trainer_snapshot(current_user)
    except Exception:
        pass


def bootstrap_latest_save(current_user: str | None) -> None:
    if not current_user:
        return
    cur = get_current_save_for_user(current_user)
    if cur:
        _ensure_local_copy(current_user, cur[1])
        return
    try:
        latest = list_saves_by_user(current_user, limit=1)
        if latest:
            last_id, fname, *_ = latest[0]
            set_current_save_for_user(current_user, last_id)
            _ensure_local_copy(current_user, fname)
    except Exception:
        pass


def write_uploaded_save_copy(current_user: str | None, original_name: str, data: bytes) -> None:
    if not current_user:
        return
    try:
        ext = Path(original_name).suffix or ".sav"
        dest = ensure_user_dir(current_user) / ts_name(current_user, ext=ext)
        dest.write_bytes(data)
    except Exception:
        pass

def _ensure_local_copy(current_user: str, filename: str) -> None:
    try:
        dest = ensure_user_dir(current_user) / filename
        if dest.exists():
            return
        data = load_save_bytes(filename)
        if data:
            dest.write_bytes(data)
    except Exception:
        pass
