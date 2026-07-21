from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


def _cache_data(ttl: int = 120):
    if st is None:
        return lambda f: f
    try:
        return st.cache_data(ttl=ttl, show_spinner=False)
    except Exception:
        return lambda f: f


@_cache_data(ttl=120)
def image_data_uri(
    path: str | None,
    mtime: float | None = None,
    *,
    min_bytes: int = 1,
) -> str:
    _ = mtime
    try:
        if not path:
            return ""
        file_path = Path(path)
        if not file_path.exists() or file_path.stat().st_size < int(min_bytes):
            return ""
        media_type = mimetypes.guess_type(str(file_path))[0] or "image/png"
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return f"data:{media_type};base64,{encoded}"
    except Exception:
        return ""
