from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request

try:
    import tomllib
except Exception:
    tomllib = None  # type: ignore[assignment]

try:
    import streamlit as st  # type: ignore
except Exception:
    st = None  # type: ignore


_NORMATIVA_HASH_KEY = "discord_notify:normativa_hash"
_WEBHOOK_TIMEOUT_SECONDS = 2.0


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


def _webhook_validation_error() -> str:
    url = _webhook_url()
    if not url:
        return "Falta DISCORD_WEBHOOK_URL en los secrets."
    if url.strip().lower() in {"tu webhook", "webhook", "pega_aqui_la_url"}:
        return "DISCORD_WEBHOOK_URL sigue con texto de ejemplo."
    if not url.startswith("https://discord.com/api/webhooks/"):
        return "DISCORD_WEBHOOK_URL no parece una URL de webhook de Discord."
    return ""


def _post_webhook_detail(payload: dict) -> tuple[bool, str]:
    url = _webhook_url()
    validation_error = _webhook_validation_error()
    if validation_error:
        return False, validation_error

    body = {"username": _webhook_username(), **payload}
    try:
        data = json.dumps(body).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json", "User-Agent": "PokeApp"},
            method="POST",
        )
        with request.urlopen(req, timeout=_WEBHOOK_TIMEOUT_SECONDS) as response:
            status = int(response.status)
            if 200 <= status < 300:
                return True, "Mensaje enviado."
            return False, f"Discord respondio con HTTP {status}."
    except error.HTTPError as exc:
        return False, f"Discord respondio con HTTP {int(exc.code)}."
    except error.URLError as exc:
        return False, f"No se pudo conectar con Discord: {exc.reason}"
    except Exception as exc:
        return False, f"Error enviando a Discord: {exc}"


def _post_webhook(payload: dict) -> bool:
    ok, _message = _post_webhook_detail(payload)
    return ok


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


def notify_purchase_async(*, user: str, item: str, price: int, purchase_id: int | None = None) -> None:
    thread = threading.Thread(
        target=notify_purchase,
        kwargs={"user": user, "item": item, "price": price, "purchase_id": purchase_id},
        daemon=True,
    )
    thread.start()


def discord_webhook_configured() -> bool:
    return not bool(_webhook_validation_error())


def discord_webhook_status() -> str:
    return _webhook_validation_error() or "Webhook configurado."


def send_test_notification() -> tuple[bool, str]:
    return _post_webhook_detail(
        {
            "embeds": [
                _embed(
                    title="Prueba de Aaron Avisa",
                    description="El webhook de Discord esta configurado correctamente en esta app.",
                    color=0x2ECC71,
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
