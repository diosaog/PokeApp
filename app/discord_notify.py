from __future__ import annotations

import hashlib
import json
import os
import threading
import time
import unicodedata
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

from app.common import COIN


_NORMATIVA_HASH_KEY = "discord_notify:normativa_hash"
_NORMATIVA_SECTION_HASHES_KEY = "discord_notify:normativa_section_hashes"
_WEBHOOK_TIMEOUT_SECONDS = float(os.environ.get("DISCORD_WEBHOOK_TIMEOUT_SECONDS", "8"))
_WEBHOOK_RETRIES = max(1, int(os.environ.get("DISCORD_WEBHOOK_RETRIES", "3")))


def _normalize_normativa_text(normativa_text: str) -> str:
    normalized = (normativa_text or "").replace("\r\n", "\n").replace("\r", "\n")
    normalized = unicodedata.normalize("NFC", normalized)
    lines = [line.rstrip() for line in normalized.split("\n")]

    collapsed_lines: list[str] = []
    previous_blank = False
    for line in lines:
        is_blank = not line.strip()
        if is_blank:
            if previous_blank:
                continue
            previous_blank = True
            collapsed_lines.append("")
            continue

        previous_blank = False
        collapsed_lines.append(line)

    return "\n".join(collapsed_lines).strip()


def _legacy_normativa_hash(normativa_text: str) -> str:
    normalized = (normativa_text or "").strip().replace("\r\n", "\n")
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normativa_hash(normativa_text: str) -> str:
    normalized = _normalize_normativa_text(normativa_text)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _normalize_section_payloads(section_payloads: dict | None) -> dict[str, dict[str, str]]:
    normalized: dict[str, dict[str, str]] = {}
    for key, payload in (section_payloads or {}).items():
        if not isinstance(payload, dict):
            continue
        section_id = str(key).strip()
        if not section_id:
            continue
        title = str(payload.get("title") or section_id).strip() or section_id
        text = str(payload.get("text") or "")
        normalized[section_id] = {"title": title, "hash": _normativa_hash(text)}
    return normalized


def _load_section_hashes(raw: str | None) -> dict[str, dict[str, str]]:
    try:
        obj = json.loads(raw or "")
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}

    out: dict[str, dict[str, str]] = {}
    for key, payload in obj.items():
        if not isinstance(payload, dict):
            continue
        section_id = str(key).strip()
        title = str(payload.get("title") or section_id).strip() or section_id
        digest = str(payload.get("hash") or "").strip()
        if section_id and digest:
            out[section_id] = {"title": title, "hash": digest}
    return out


def _changed_normativa_sections(
    current_sections: dict[str, dict[str, str]],
    previous_sections: dict[str, dict[str, str]],
) -> list[str]:
    changed: list[str] = []

    for section_id, payload in current_sections.items():
        previous = previous_sections.get(section_id)
        if previous is None or previous.get("hash") != payload.get("hash"):
            changed.append(str(payload.get("title") or section_id))

    for section_id, payload in previous_sections.items():
        if section_id not in current_sections:
            changed.append(str(payload.get("title") or section_id))

    return changed


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
    if not (
        url.startswith("https://discord.com/api/webhooks/")
        or url.startswith("https://discordapp.com/api/webhooks/")
    ):
        return "DISCORD_WEBHOOK_URL no parece una URL de webhook de Discord."
    return ""


def _post_webhook_once(payload: dict) -> tuple[bool, str]:
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
        detail = ""
        try:
            detail = exc.read(300).decode("utf-8", errors="replace").strip()
        except Exception:
            detail = ""
        suffix = f": {detail}" if detail else "."
        return False, f"Discord respondio con HTTP {int(exc.code)}{suffix}"
    except error.URLError as exc:
        return False, f"No se pudo conectar con Discord: {exc.reason}"
    except Exception as exc:
        return False, f"Error enviando a Discord: {exc}"


def _post_webhook_detail(payload: dict) -> tuple[bool, str]:
    last_message = ""
    for attempt in range(1, _WEBHOOK_RETRIES + 1):
        ok, message = _post_webhook_once(payload)
        if ok:
            return True, message
        last_message = message
        if "HTTP 4" in message and "HTTP 429" not in message:
            break
        if attempt < _WEBHOOK_RETRIES:
            time.sleep(0.5 * attempt)
    return False, last_message or "No se pudo enviar a Discord."


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


def _field_value(lines: list[str], *, code_block: bool = False, limit: int = 1000) -> str:
    text = "\n".join(str(line) for line in lines if str(line).strip()).strip() or "-"
    if len(text) > limit:
        text = text[: max(0, limit - 16)].rstrip() + "\n... (recortado)"
    if code_block:
        return f"```text\n{text}\n```"
    return text


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


def _coin_label(value: int) -> str:
    return f"{int(value)} {COIN}"


def notify_shop_discounts_created(
    *, jornada: int, discounts: list[dict], activates_at: int
) -> bool:
    if not discounts:
        return False
    category_labels = {
        "comodines": "Comodines",
        "competitivos": "Objetos",
        "crianza": "Crianza",
    }
    grouped: dict[tuple[str, str], list[str]] = {}
    for discount in discounts:
        category = str(discount.get("category") or "competitivos")
        kind = str(discount.get("discount_kind") or "normal")
        grouped.setdefault((category, kind), []).append(
            f"{discount.get('item') or '-'}: "
            f"{_coin_label(int(discount.get('base_price') or 0))} -> "
            f"{_coin_label(int(discount.get('discount_price') or 0))}"
        )
    fields = []
    for category in ("comodines", "competitivos", "crianza"):
        for kind in ("normal", "mega"):
            lines = grouped.get((category, kind), [])
            if not lines:
                continue
            label = "Mega Rebajas" if kind == "mega" else "Rebajas"
            fields.append(
                {
                    "name": f"{category_labels[category]} · {label}",
                    "value": _field_value([f"- {line}" for line in lines]),
                    "inline": False,
                }
            )
    activation = int(activates_at)
    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title="El Poké Mart prepara una nueva remesa",
                    description=(
                        f"Los proveedores de Teselia están preparando las promociones "
                        f"de la Jornada {int(jornada)}.\n\n"
                        f"**Apertura:** <t:{activation}:F> · <t:{activation}:R>\n"
                        "Hasta entonces, Objetos y Crianza estarán marcados como "
                        "**stock en traslado**. Los Comodines seguirán disponibles "
                        "a su precio habitual."
                    ),
                    color=0xF39C12,
                    fields=fields,
                )
            ]
        }
    )


def notify_shop_discounts_created_async(
    *, jornada: int, discounts: list[dict], activates_at: int
) -> None:
    if not discounts:
        return
    thread = threading.Thread(
        target=notify_shop_discounts_created,
        kwargs={
            "jornada": jornada,
            "discounts": list(discounts),
            "activates_at": int(activates_at),
        },
        daemon=True,
    )
    thread.start()


def notify_discount_purchase(
    *,
    user: str,
    item: str,
    base_price: int,
    discount_price: int,
    discount_kind: str,
    purchase_id: int | None = None,
) -> bool:
    label = "🔥 Mega Rebaja" if str(discount_kind) == "mega" else "🔥 Rebaja"
    fields = [
        {"name": "Jugador", "value": user or "-", "inline": True},
        {"name": "Objeto", "value": item or "-", "inline": True},
        {
            "name": "Precio",
            "value": f"{_coin_label(int(base_price))} -> {_coin_label(int(discount_price))}",
            "inline": True,
        },
    ]
    if purchase_id is not None:
        fields.append({"name": "Compra", "value": f"#{int(purchase_id)}", "inline": True})
    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title=f"Compra con {label}",
                    description=f"{user} ha comprado {item} en rebaja.",
                    color=0xE67E22,
                    fields=fields,
                )
            ]
        }
    )


def notify_discount_purchase_async(
    *,
    user: str,
    item: str,
    base_price: int,
    discount_price: int,
    discount_kind: str,
    purchase_id: int | None = None,
) -> None:
    thread = threading.Thread(
        target=notify_discount_purchase,
        kwargs={
            "user": user,
            "item": item,
            "base_price": int(base_price),
            "discount_price": int(discount_price),
            "discount_kind": discount_kind,
            "purchase_id": purchase_id,
        },
        daemon=True,
    )
    thread.start()


def notify_team_locked(
    *,
    user: str,
    jornada: int,
    is_late: bool,
) -> bool:
    suffix = " tarde" if is_late else ""
    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title=f"Equipo fijado - Jornada {int(jornada)}",
                    description=f"{user} ha fijado su equipo{suffix} para la jornada {int(jornada)}.",
                    color=0x2ECC71 if not is_late else 0xE67E22,
                    fields=[
                        {"name": "Entrenador", "value": user or "-", "inline": True},
                        {"name": "Estado", "value": "Fijado tarde" if is_late else "Fijado", "inline": True},
                    ],
                )
            ]
        }
    )


def notify_team_locked_async(*, user: str, jornada: int, is_late: bool) -> None:
    thread = threading.Thread(
        target=notify_team_locked,
        kwargs={"user": user, "jornada": int(jornada), "is_late": bool(is_late)},
        daemon=True,
    )
    thread.start()


def notify_missing_team_locks(*, jornada: int, missing: list[str]) -> bool:
    if not missing:
        description = f"Todos han fijado equipo para la jornada {int(jornada)}."
        fields = None
        color = 0x2ECC71
    else:
        description = f"Faltan equipos por fijar para la jornada {int(jornada)}."
        fields = [{"name": "Faltan", "value": _field_value([f"- {u}" for u in missing]), "inline": False}]
        color = 0xE74C3C
    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title=f"Team Preview - Jornada {int(jornada)}",
                    description=description,
                    color=color,
                    fields=fields,
                )
            ]
        }
    )


def notify_missing_team_locks_async(*, jornada: int, missing: list[str]) -> None:
    thread = threading.Thread(
        target=notify_missing_team_locks,
        kwargs={"jornada": int(jornada), "missing": list(missing)},
        daemon=True,
    )
    thread.start()


def league_round_finished_payload(
    *,
    round_no: int,
    rows: list[dict],
    round_results: list[dict] | None = None,
    summary_lines: list[str] | None = None,
) -> dict:
    lines = []
    for row in rows[:20]:
        pos = row.get("pos", "-")
        user = str(row.get("user") or "-")
        points = str(row.get("points") or "0.0")
        coins = int(row.get("coins") or 0)
        lines.append(f"{pos:>2}. {user:<14} {points:>5} pts | {coins:>3} monedas")

    fields: list[dict] = []
    if summary_lines:
        fields.append(
            {
                "name": "Resumen",
                "value": _field_value(summary_lines),
                "inline": False,
            }
        )

    for group in round_results or []:
        division = str(group.get("division") or "Resultados")
        result_lines = [f"- {line}" for line in group.get("lines") or []]
        if result_lines:
            fields.append(
                {
                    "name": f"Resultados {division}",
                    "value": _field_value(result_lines),
                    "inline": False,
                }
            )

    fields.append(
        {
            "name": "Posiciones, puntos y monedas",
            "value": _field_value(lines or ["Sin datos."], code_block=True),
            "inline": False,
        }
    )

    return {
        "embeds": [
            _embed(
                title=f"Jornada {int(round_no)} finalizada",
                description="Resultados y tabla general actualizados.",
                color=0xE67E22,
                fields=fields,
            )
        ]
    }


def notify_league_round_finished_detail(
    *,
    round_no: int,
    rows: list[dict],
    round_results: list[dict] | None = None,
    summary_lines: list[str] | None = None,
) -> tuple[bool, str]:
    return _post_webhook_detail(
        league_round_finished_payload(
            round_no=round_no,
            rows=rows,
            round_results=round_results,
            summary_lines=summary_lines,
        )
    )


def notify_league_round_finished(
    *,
    round_no: int,
    rows: list[dict],
    round_results: list[dict] | None = None,
    summary_lines: list[str] | None = None,
) -> bool:
    ok, _message = notify_league_round_finished_detail(
        round_no=round_no,
        rows=rows,
        round_results=round_results,
        summary_lines=summary_lines,
    )
    return ok


def notify_league_round_finished_async(
    *,
    round_no: int,
    rows: list[dict],
    round_results: list[dict] | None = None,
    summary_lines: list[str] | None = None,
) -> None:
    thread = threading.Thread(
        target=notify_league_round_finished,
        kwargs={
            "round_no": round_no,
            "rows": rows,
            "round_results": round_results,
            "summary_lines": summary_lines,
        },
        daemon=True,
    )
    thread.start()


def league_match_result_payload(
    *,
    round_no: int,
    division: str,
    player1: str,
    player2: str,
    winner: str,
) -> dict:
    loser = player2 if winner == player1 else player1
    return {
        "embeds": [
            _embed(
                title=f"Resultado guardado - Jornada {int(round_no)}",
                description=f"{winner} ha ganado a {loser}.",
                color=0x2ECC71,
                fields=[
                    {"name": "Liga", "value": division or "-", "inline": True},
                    {"name": "Enfrentamiento", "value": f"{player1} vs {player2}", "inline": True},
                    {"name": "Ganador", "value": winner or "-", "inline": True},
                ],
            )
        ]
    }


def notify_league_match_result_detail(
    *,
    round_no: int,
    division: str,
    player1: str,
    player2: str,
    winner: str,
) -> tuple[bool, str]:
    return _post_webhook_detail(
        league_match_result_payload(
            round_no=round_no,
            division=division,
            player1=player1,
            player2=player2,
            winner=winner,
        )
    )


def notify_league_match_result(
    *,
    round_no: int,
    division: str,
    player1: str,
    player2: str,
    winner: str,
) -> bool:
    ok, _message = notify_league_match_result_detail(
        round_no=round_no,
        division=division,
        player1=player1,
        player2=player2,
        winner=winner,
    )
    return ok


def _notify_league_match_results_batch(results: list[dict]) -> None:
    for idx, result in enumerate(results):
        notify_league_match_result(
            round_no=int(result.get("round_no") or 0),
            division=str(result.get("division") or "-"),
            player1=str(result.get("player1") or "-"),
            player2=str(result.get("player2") or "-"),
            winner=str(result.get("winner") or "-"),
        )
        if idx < len(results) - 1:
            time.sleep(0.35)


def notify_league_match_results_async(results: list[dict]) -> None:
    if not results:
        return
    thread = threading.Thread(
        target=_notify_league_match_results_batch,
        kwargs={"results": list(results)},
        daemon=True,
    )
    thread.start()


def notify_trainer_retired(*, trainer: str, by_user: str | None = None) -> bool:
    fields = []
    if by_user:
        fields.append({"name": "Registrado por", "value": str(by_user), "inline": True})
    return _post_webhook(
        {
            "embeds": [
                _embed(
                    title="Entrenador retirado",
                    description=(
                        f"{trainer} se ha retirado de la liga. "
                        "Sus resultados anteriores se conservan, pero deja de contar "
                        "para jornadas, puntos, monedas y sistemas activos."
                    ),
                    color=0x95A5A6,
                    fields=fields,
                )
            ]
        }
    )


def notify_trainer_retired_async(*, trainer: str, by_user: str | None = None) -> None:
    thread = threading.Thread(
        target=notify_trainer_retired,
        kwargs={"trainer": trainer, "by_user": by_user},
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


def sync_normativa_notification(normativa_text: str, section_payloads: dict | None = None) -> bool:
    from storage import settings_get, settings_set

    current_hash = _normativa_hash(normativa_text)
    legacy_hash = _legacy_normativa_hash(normativa_text)
    current_sections = _normalize_section_payloads(section_payloads)

    try:
        previous_hash = settings_get(_NORMATIVA_HASH_KEY)
    except Exception:
        previous_hash = None
    try:
        previous_sections_raw = settings_get(_NORMATIVA_SECTION_HASHES_KEY)
    except Exception:
        previous_sections_raw = None
    previous_sections = _load_section_hashes(previous_sections_raw)

    if not previous_hash:
        try:
            settings_set(_NORMATIVA_HASH_KEY, current_hash)
            if current_sections:
                settings_set(_NORMATIVA_SECTION_HASHES_KEY, json.dumps(current_sections, ensure_ascii=False))
        except Exception:
            pass
        return False

    if previous_hash in {current_hash, legacy_hash}:
        if previous_hash != current_hash or (current_sections and current_sections != previous_sections):
            try:
                settings_set(_NORMATIVA_HASH_KEY, current_hash)
                if current_sections:
                    settings_set(_NORMATIVA_SECTION_HASHES_KEY, json.dumps(current_sections, ensure_ascii=False))
            except Exception:
                pass
        return False

    changed_sections = _changed_normativa_sections(current_sections, previous_sections)
    if changed_sections:
        fields = [
            {
                "name": "Secciones modificadas",
                "value": "\n".join(f"- {title}" for title in changed_sections[:10]),
                "inline": False,
            }
        ]
    else:
        fields = [
            {
                "name": "Secciones modificadas",
                "value": "Cambio detectado en la normativa general, sin desglose previo por secciones.",
                "inline": False,
            }
        ]

    sent = _post_webhook(
        {
            "embeds": [
                _embed(
                    title="Normativa actualizada",
                    description=(
                        "La normativa de ChampionsLocke ha cambiado. "
                        "Revisad la seccion de normativa de PokeApp para ver los cambios."
                    ),
                    color=0x3498DB,
                    fields=fields,
                )
            ]
        }
    )

    try:
        settings_set(_NORMATIVA_HASH_KEY, current_hash)
        if current_sections:
            settings_set(_NORMATIVA_SECTION_HASHES_KEY, json.dumps(current_sections, ensure_ascii=False))
    except Exception:
        pass
    return sent
