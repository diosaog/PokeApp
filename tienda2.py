from __future__ import annotations

from typing import Any


def page_tienda() -> None:
    from app.tienda.ui import page_tienda as _page_tienda

    _page_tienda()


def _render_redeem_flow(*args: Any, **kwargs: Any) -> Any:
    from app.tienda.redeem import render_redeem_flow

    return render_redeem_flow(*args, **kwargs)

__all__ = ["page_tienda", "_render_redeem_flow"]
