from __future__ import annotations

from urllib.parse import urlparse
from urllib import request
import json
import re
import streamlit as st


def ensure_pokepaste_state() -> None:
    st.session_state.setdefault("pokepastes", {})
    try:
        trainer = st.session_state.get("trainer_selected") or st.session_state.get("user") or ""
        if trainer and trainer not in st.session_state["pokepastes"]:
            from storage import settings_get
            key = f"pokepaste:{trainer}"
            raw = settings_get(key)
            if raw:
                obj = json.loads(raw)
                if isinstance(obj, dict):
                    st.session_state["pokepastes"][trainer] = obj
    except Exception:
        pass


def fetch_pokepaste_text(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        url = "https://" + url
    if "/raw" not in url:
        url = url.rstrip("/") + "/raw"
    with request.urlopen(url) as resp:  # type: ignore[call-arg]
        return resp.read().decode("utf-8", errors="ignore")


def parse_pokepaste(txt: str) -> list[dict]:
    if "<!DOCTYPE" in txt or "<html" in txt.lower():
        raise ValueError("Link does not return plain text. Use the /raw URL from Pokepaste.")
    blocks = [b.strip() for b in re.split(r"\n\s*\n", txt) if b.strip()]
    team = []
    for b in blocks:
        lines = [ln.strip() for ln in b.splitlines() if ln.strip()]
        if not lines:
            continue
        head = lines[0]
        species, item = head, None
        if "@" in head:
            parts = head.split("@", 1)
            species = parts[0].strip()
            item = parts[1].strip()
        ability = None
        moves = []
        for ln in lines[1:]:
            if ln.lower().startswith("ability:"):
                ability = ln.split(":", 1)[1].strip()
            elif ln.startswith("-"):
                mv = ln[1:].strip()
                if mv:
                    moves.append(mv)
                    if len(moves) >= 4:
                        break
        team.append({"species": species, "item": item, "ability": ability, "moves": moves})
    return team


def _clean_text(val: str | None) -> str:
    if not val:
        return ""
    txt = str(val)
    txt = re.sub(r"<[^>]+>", "", txt)
    return txt.strip()


def sanitize_mon(mon: dict) -> dict:
    sp_raw = _clean_text(mon.get("species"))
    nickname = ""
    species_clean = sp_raw
    try:
        m = re.match(r"^(.*?)\(([^)]+)\)", sp_raw)
        if m:
            nickname = m.group(1).strip()
            species_clean = m.group(2).strip()
    except Exception:
        species_clean = sp_raw
    item = _clean_text(mon.get("item"))
    ability = _clean_text(mon.get("ability"))
    moves_raw = mon.get("moves") or []
    moves: list[str] = []
    for m in moves_raw:
        cm = _clean_text(m)
        if cm:
            moves.append(cm)
    title = f"{nickname} ({species_clean})" if nickname else species_clean
    return {
        "species": species_clean,
        "nickname": nickname,
        "title": title,
        "item": item,
        "ability": ability,
        "moves": moves,
    }


def pokepaste_preview(paste: dict | None) -> None:
    if not paste or not paste.get("team"):
        st.caption("Sin Pokepaste guardado.")
        return
    st.caption(f"URL: {paste.get('url')}")
    team = [sanitize_mon(mon) for mon in (paste.get("team") or [])]
    team = [m for m in team if m.get("species")]
    for mon in team:
        sp = mon.get("species") or "Pokemon"
        title = mon.get("title") or sp
        item = mon.get("item")
        ability = mon.get("ability")
        moves = mon.get("moves") or []
        from showdown_sprites import showdown_sprite_url
        img = showdown_sprite_url(species_name=str(sp), prefer_animated=False)
        with st.container():
            cols = st.columns([1, 3])
            with cols[0]:
                st.image(img, width=72)
            with cols[1]:
                st.markdown(f"**{title}** {f'@ {item}' if item else ''}")
                if ability:
                    st.caption(f"Habilidad: {ability}")
                if moves:
                    st.markdown("\n".join([f"- {m}" for m in moves]))
