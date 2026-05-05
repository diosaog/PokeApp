from __future__ import annotations

import base64
import mimetypes
from pathlib import Path
import unicodedata

PROJECT_ROOT = Path(__file__).resolve().parents[2]
LOGO_DIR_REL = Path("assets") / "copa_dobles" / "team_logos"
LOGO_DIR = PROJECT_ROOT / LOGO_DIR_REL
LOGO_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg")


def ensure_logo_dir() -> None:
    try:
        LOGO_DIR.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass


def logo_data_uri_for_team(team_name: str) -> str | None:
    logo_path = logo_for_team(team_name)
    logo_bytes = logo_bytes_for_team(team_name)
    if not logo_path or not logo_bytes:
        return None
    try:
        mime = mimetypes.guess_type(logo_path)[0] or "image/png"
        encoded = base64.b64encode(logo_bytes).decode("ascii")
        return f"data:{mime};base64,{encoded}"
    except Exception:
        return None


def logo_bytes_for_team(team_name: str) -> bytes | None:
    logo_path = logo_for_team(team_name)
    if not logo_path:
        return None
    try:
        return Path(logo_path).read_bytes()
    except Exception:
        return None


def logo_for_team(team_name: str) -> str | None:
    ensure_logo_dir()
    slug = slugify(team_name)
    if not slug:
        return None
    for ext in LOGO_EXTS:
        candidate = LOGO_DIR / f"{slug}{ext}"
        if candidate.exists():
            return str(candidate)
    try:
        for candidate in LOGO_DIR.iterdir():
            if candidate.is_file() and candidate.suffix.lower() in LOGO_EXTS and slugify(candidate.stem) == slug:
                return str(candidate)
    except Exception:
        pass
    return None


def slugify(text: str) -> str:
    t = unicodedata.normalize("NFD", str(text or "").strip().lower())
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Mn")
    out: list[str] = []
    prev_dash = False
    for ch in t:
        if ch.isalnum():
            out.append(ch)
            prev_dash = False
        elif not prev_dash:
            out.append("-")
            prev_dash = True
    return "".join(out).strip("-")
