from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib import request

try:
    import tomllib
except Exception:
    tomllib = None  # type: ignore[assignment]

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


_NORMATIVA_HASH_KEY = "discord_notify:normativa_hash"


def _secret(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if value:
        return value
    if st is None:
        raw_secret = ""
    else:
        try:
            raw = st.secrets.get(name, "")
            raw_secret = str(raw).strip() if raw is not None else ""
        except Exception:
            raw_secret = ""
    if raw_secret:
        return raw_secret

    if tomllib is None:
        return ""
    try:
        secrets_path = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
        with secrets_path.open("rb") as fh:
            raw = tomllib.load(fh).get(name, "")
        return str(raw).strip() if raw is not None else ""
    except Exception:
        return ""


def _webhook_url() -> str:
    return _secret("DISCORD_WEBHOOK_URL")


def _webhook_username() -> str:
    return _secret("DISCORD_WEBHOOK_USERNAME") or "PokeApp"


def _post_webhook(payload: dict) -> bool:
    url = _webhook_url()
    if not url:
        return False

    body = {"username": _webhook_username(), **payload}
    try:
        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "PokeApp"},
            method="POST",
        )
        with request.urlopen(req, timeout=5.0) as response:
            return 200 <= int(response.status) < 300
    except Exception:
        return False


def _embed(*, title: str, description: str, color: int, fields: list[dict] | None = None) -> dict:
    data = {
        "title": title,
        "description": description,
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if fields:
        data["fields"] = fields
    return data


def notify_purchase(*, user: str, item: str, price: int, purchase_id: int | None = None) -> bool:
    price_value = int(price or 0)
    price_label = "Gratis" if price_value <= 0 else f"{price_value} monedas"
    fields = [
        {"name": "Jugador", "value": user or "-", "inline": True},
        {"name": "Objeto", "value": item or "-", "inline": True},
        {"name": "Precio", "value": price_label, "inline": True},
    ]
    if purchase_id is not None:
        fields.append({"name": "Compra", "value": f"#{int(purchase_id)}", "inline": True})

    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title="Nueva compra en tienda",
                    description="Se ha registrado una compra en PokeApp.",
                    color=0xF1C40F,
                    fields=fields,
                )
            ]
        }
    )


def sync_normativa_notification(normativa_text: str) -> bool:
    from storage import settings_get, settings_set

    normalized = (normativa_text or "").strip().replace("\r\n", "\n")
    current_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    try:
        previous_hash = settings_get(_NORMATIVA_HASH_KEY)
    except Exception:
        previous_hash = None

    if not previous_hash:
        try:
            settings_set(_NORMATIVA_HASH_KEY, current_hash)
        except Exception:
            pass
        return False

    if previous_hash == current_hash:
        return False

    sent = _post_webhook(
        {
            "embeds": [
                _embed(
                    title="Normativa actualizada",
                    description=(
                        "La normativa de ChampionsLocke ha cambiado. "
                        "Revisad la seccion de inicio de PokeApp para ver los cambios."
                    ),
                    color=0x3498DB,
                )
            ]
        }
    )

    try:
        settings_set(_NORMATIVA_HASH_KEY, current_hash)
    except Exception:
        pass
    return sent
