from __future__ import annotations

def page_copa() -> None:
    from app.copa.swiss import page_copa as _page_copa

    _page_copa()

__all__ = ["page_copa"]
