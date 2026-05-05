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
.bill-title {
  display:inline-block;
  background:linear-gradient(180deg,var(--accent) 0%, var(--accent-dark) 100%);
  border:1px solid var(--bw2-edge-strong);
  border-radius:0;
  padding:10px 12px;
  color:#fff;
  font-family:var(--font-pixel);
  font-size:12px;
  font-weight:700;
  letter-spacing:0.4px;
  text-transform:uppercase;
  clip-path: polygon(10px 0, 100% 0, 100% calc(100% - 10px), calc(100% - 10px) 100%, 0 100%, 0 10px);
}
.bill-subtitle {
  margin-top:8px;
  display:inline-block;
  background:linear-gradient(180deg,var(--bw2-panel-2) 0%, var(--bw2-panel) 100%);
  border:1px solid var(--bw2-edge);
  border-radius:0;
  padding:8px 10px;
  color:var(--bw2-text);
  font-family:var(--font-pixel);
  font-size:10px;
  font-weight:700;
  text-transform:uppercase;
}
.bill-divider { height:2px; background:linear-gradient(90deg, transparent 0%, var(--accent) 22%, var(--accent) 78%, transparent 100%); margin:12px 0 16px; }
.bill-chip {
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
.bill-chip b { color:#fff; }
.bill-save-meta {
  margin-top:8px;
  background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%);
  border:1px solid var(--bw2-edge);
  border-radius:0;
  padding:8px 10px;
  color:var(--bw2-text-soft);
  font-family:var(--font-ui);
  font-size:18px;
  font-weight:400;
  line-height:1.45;
  letter-spacing:0.1px;
}
.bill-save-meta b { color:#fff; font-weight:700; font-family:var(--font-pixel); font-size:10px; }
div[data-testid="stFileUploaderDropzone"] {
  background:linear-gradient(180deg,var(--bw2-screen-2) 0%, var(--bw2-screen) 100%) !important;
  border:1px dashed var(--bw2-edge) !important;
  border-radius:0 !important;
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
</style>
"""


def clear_save_related_caches() -> None:
    clear_money_caches()
    clear_ranking_caches()
    try:
        import utils as _utils

        cache_fn = getattr(_utils, "_list_user_saves_cached", None)
        if cache_fn is not None:
            cache_fn.clear()
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


def current_save_meta_html(row: tuple) -> str:
    id_, fname, oname, sha, up, ts = row
    return (
        f"<div class='bill-save-meta'><b>ID:</b> {_html.escape(str(id_))} | "
        f"<b>Nombre:</b> {_html.escape(str(oname or fname))} | "
        f"<b>Subido por:</b> {_html.escape(str(up or '-'))} | "
        f"<b>Fecha:</b> {_html.escape(str(datetime.fromtimestamp(ts)))} | "
        f"<b>SHA:</b> {_html.escape(str(sha[:8]))}</div>"
    )


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
