"""Competition announcements for Discord («Aaron Avisa!»): facts, embeds, delivery.

Each outbox row (067) names one confirmed fact. Facts are read from the
records that confirmed it (the matchday snapshot revision, the frozen season
finalization, the cup history and certificate, the team lock, the
redemption, the public trial decision) and computed as of that moment, never
from live state that may have moved on. Only what PokeApp shows to every
trainer reaches Discord: public team snapshots, official results and
rewards, public trial cases, never private snapshots, saves or evidence.

Delivery is at most once per announcement: a post whose outcome is unknown
is marked ``uncertain`` and never sent again. A replaced team lock edits the
message already sent (edits are idempotent and may be retried).
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
import logging
import re

from app.repositories.errors import PersistenceError

logger = logging.getLogger(__name__)

# Liga Nocturna tokens (web/src/design/tokens.css).
ACCENT, WARM, INFO, VIOLET = 0x2DE2C8, 0xFF9A4D, 0x5F9DFF, 0xA68BFF
GOLD, MAGENTA, DANGER, LEAF, MUTED = 0xFFCC3D, 0xFF3D8B, 0xFF5C8A, 0x9BE15D, 0x9AA4D8

MAX_ATTEMPTS = 8
BACKOFF_SECONDS = (10, 30, 120, 300, 900, 1800, 3600, 7200)
LEASE = timedelta(minutes=3)
# A post still undelivered after this long is history, not news.
MAX_AGE = timedelta(hours=24)
BATCH = 10

STATUS_LABELS = {
    "retired": "se retira de la competición",
    "abandoned": "abandona la competición",
    "disqualified": "queda fuera de la competición por descalificación",
}
PHASES = {
    "swiss": "Ronda suiza",
    "elimination": "Eliminatoria",
    "semifinal": "Semifinales",
    "round_robin": "Liguilla",
    "final": "Final",
}


class Skip(Exception):
    """The fact is no longer announceable; the row is closed with this code."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


# -- text helpers ------------------------------------------------------------

_MARKDOWN = re.compile(r"([\\*_~`|>\[\]()#])")


def clean(value, limit: int = 64) -> str:
    """User text for Discord markdown: escaped, mention-proof, single line."""
    text = " ".join(str(value or "").split())
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    # allowed_mentions already blocks pings; this also keeps the text inert.
    return _MARKDOWN.sub(r"\\\1", text).replace("@", "@​")


def number(value) -> str:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return str(value)
    text = format(amount.quantize(Decimal("0.01")).normalize(), "f")
    return "0" if text in ("-0", "") else text


def signed(value) -> str:
    text = number(value)
    return text if text.startswith("-") or text == "0" else "+" + text


def ranks(values: list) -> list[int]:
    """Shared rank for equal values (1, 2, 2, 4): shown order never breaks a tie."""
    out, last = [], None
    for index, value in enumerate(values, 1):
        out.append(out[-1] if last is not None and value == last else index)
        last = value
    return out


def medal(position: int) -> str:
    return {1: "🥇", 2: "🥈", 3: "🥉"}.get(position, f"{position}.")


def instant(value) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=UTC)


# -- embed limits (Discord: 256 title, 4096 description, 25 fields of
# 256/1024, 2048 footer, 6000 characters in total) -----------------------------


def lines_fields(name: str, lines: list[str], *, inline: bool = False) -> list[dict]:
    """Pack lines into as many ≤1024-character fields as needed."""
    fields, chunk = [], ""
    for line in lines or ["—"]:
        line = line[:1000]
        if chunk and len(chunk) + 1 + len(line) > 1024:
            fields.append(chunk)
            chunk = line
        else:
            chunk = f"{chunk}\n{line}" if chunk else line
    fields.append(chunk)
    return [
        {
            "name": (name if i == 0 else f"{name} (cont.)")[:256],
            "value": value,
            "inline": inline,
        }
        for i, value in enumerate(fields)
    ]


MORE = {"name": "…", "value": "Más detalles en PokeApp.", "inline": False}


def embed(
    *, title, description, color, fields=(), footer="PokeApp", timestamp=None
) -> dict:
    data = {
        "title": title[:256],
        "description": description[:4096],
        "color": color,
        "footer": {"text": footer[:2048]},
    }
    if timestamp:
        data["timestamp"] = timestamp.astimezone(UTC).isoformat()
    size = len(data["title"]) + len(data["description"]) + len(data["footer"]["text"])
    fields = [f for f in fields if f.get("value")]
    kept = []
    for index, field in enumerate(fields):
        last = index == len(fields) - 1
        cost = len(field["name"]) + len(field["value"])
        # Always keep room for the closing «…» field when more would follow.
        reserve = 0 if last else len(MORE["name"]) + len(MORE["value"])
        if (not last and len(kept) == 24) or size + cost + reserve > 6000:
            kept.append(dict(MORE))
            break
        kept.append(field)
        size += cost
    if kept:
        data["fields"] = kept
    return {"embeds": [data]}


# -- reads ------------------------------------------------------------------------


def one(rows: list[dict], code: str = "source_missing") -> dict:
    if len(rows) != 1:
        raise Skip(code)
    return rows[0]


class Facts:
    """Bounded reads of confirmed records; ``read(table, columns, **filters)``."""

    def __init__(self, read):
        self.read = read

    def season(self, season_id) -> dict:
        season = one(self.read("seasons", "id,name,status", id=season_id))
        if season["status"] == "discarded":
            raise Skip("season_discarded")
        return season

    def names(self, trainer_ids) -> dict[str, str]:
        ids = sorted({str(t) for t in trainer_ids if t})
        if not ids:
            return {}
        return {
            r["id"]: r["display_name"]
            for r in self.read("trainers", "id,display_name", id=ids)
        }

    def players(self, season_id) -> dict[str, dict]:
        players = {
            p["id"]: p
            for p in self.read(
                "season_players", "id,trainer_id,status", season_id=season_id
            )
        }
        names = self.names(p["trainer_id"] for p in players.values())
        for p in players.values():
            p["name"] = names.get(p["trainer_id"], "Entrenador")
        return players

    def leagues(self, season_id) -> dict[str, str]:
        codes = sorted(
            d["code"] for d in self.read("divisions", "code", season_id=season_id)
        )
        if codes == ["A"]:
            return {"A": "Liga"}
        return {code: f"Liga {code}" for code in codes}


def gather(kind: str, subject: dict, read, *, revision: int = 1) -> dict:
    facts = Facts(read)
    handler = {
        "season_started": _season_started,
        "team_locked": _team_locked,
        "matchday_closed": _matchday,
        "matchday_corrected": _matchday,
        "season_finished": _season_finished,
        "cup_round_closed": _cup_round,
        "cup_finished": _cup_finished,
        "robbery_completed": _robbery,
        "trial_resolved": _trial,
        "participant_status": _participant_status,
    }.get(kind)
    if handler is None:
        raise Skip("unknown_kind")
    return {"kind": kind, "revision": revision, **handler(facts, subject)}


def _season_started(f: Facts, s: dict) -> dict:
    season = f.season(s["season_id"])
    players = f.players(season["id"])
    leagues = f.leagues(season["id"])
    configs = [
        c
        for c in f.read(
            "season_config_versions",
            "version_number,effective_from_matchday,total_matchdays",
            season_id=season["id"],
        )
        if c["effective_from_matchday"] <= 1
    ]
    if not configs:
        raise Skip("config_missing")
    config = max(configs, key=lambda c: c["version_number"])
    divisions = {
        d["id"]: d["code"]
        for d in f.read("divisions", "id,code", season_id=season["id"])
    }
    rosters = defaultdict(list)
    for m in f.read(
        "division_memberships",
        "season_player_id,division_id",
        season_id=season["id"],
        effective_from_matchday_number=1,
    ):
        if m["season_player_id"] in players:
            rosters[divisions.get(m["division_id"], "A")].append(
                players[m["season_player_id"]]["name"]
            )
    return dict(
        season=season["name"],
        total_matchdays=config["total_matchdays"],
        players=len(players),
        leagues={
            leagues.get(c, f"Liga {c}"): sorted(n, key=str.lower)
            for c, n in sorted(rosters.items())
        },
    )


def _team_locked(f: Facts, s: dict) -> dict:
    lock = one(
        f.read(
            "team_locks",
            "id,season_id,matchday_id,trainer_id,public_team_snapshot,is_late,locked_at,created_at",
            id=s["lock_id"],
        )
    )
    season = f.season(lock["season_id"])
    day = one(f.read("matchdays", "number,status", id=lock["matchday_id"]))
    players = f.players(season["id"])
    active = [p for p in players.values() if p["status"] == "active"]
    # Teams fixed for that matchday when this one was first fixed.
    created = instant(lock["created_at"])
    stamps = [
        instant(o["created_at"])
        for o in f.read(
            "team_locks", "trainer_id,created_at", matchday_id=lock["matchday_id"]
        )
    ]
    fixed = sum(
        1 for stamp in stamps if created is None or stamp is None or stamp <= created
    )
    team = lock["public_team_snapshot"]
    if not isinstance(team, list) or not all(
        isinstance(m, dict) and m.get("species") for m in team
    ):
        raise Skip("invalid_team")
    trainer = next(
        (p["name"] for p in players.values() if p["trainer_id"] == lock["trainer_id"]),
        "Entrenador",
    )
    return dict(
        season=season["name"],
        matchday=day["number"],
        trainer=trainer,
        late=bool(lock["is_late"]),
        team=team,
        fixed=fixed,
        participants=len(active),
        at=instant(lock["locked_at"]),
    )


def _matchday(f: Facts, s: dict) -> dict:
    day = one(f.read("matchdays", "id,season_id,number", id=s["matchday_id"]))
    season = f.season(day["season_id"])
    current = one(f.read("matchday_snapshots", "revision", matchday_id=day["id"]))
    if current["revision"] != s["revision"]:
        raise Skip("superseded")  # a later correction carries its own announcement
    snapshot = one(
        f.read(
            "matchday_snapshot_revisions",
            "snapshot",
            matchday_id=day["id"],
            revision=s["revision"],
        )
    )["snapshot"]
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 2:
        raise Skip("unsupported_snapshot")
    players = f.players(season["id"])
    leagues = f.leagues(season["id"])
    closed_at = instant(snapshot.get("closed_at"))
    standings = snapshot["standings"]
    numbers = {
        d["id"]: d["number"]
        for d in f.read("matchdays", "id,number", season_id=season["id"])
    }
    # Official accumulated points as of this day: the public_sanctioned_points
    # rule (frozen captures only) cut at this matchday.
    earned = defaultdict(Decimal)
    for other in f.read(
        "matchday_snapshots", "matchday_id,snapshot", season_id=season["id"]
    ):
        if (
            other["matchday_id"] != day["id"]
            and numbers.get(other["matchday_id"], 10**9) < day["number"]
        ):
            for row in other["snapshot"].get("standings", []):
                earned[row["trainer_id"]] += Decimal(str(row["points_awarded"]))
    # Wallet right after this close: every movement up to the close itself.
    balance = defaultdict(int)
    if closed_at:
        for t in f.read(
            "coin_transactions",
            "season_player_id,amount",
            season_id=season["id"],
            created_at__lte=closed_at.isoformat(),
        ):
            balance[t["season_player_id"]] += int(t["amount"])
    rows = []
    for row in standings:
        pid = row["trainer_id"]
        penalties = row.get("penalties") or {}
        total = (
            earned[pid]
            + Decimal(str(row["points_awarded"]))
            - Decimal(str(penalties.get("points_reduction") or 0))
            - Decimal(str(penalties.get("dead_points_penalty") or 0))
        )
        # A neutral tie shares its sporting rank (e.g. 4–5) in the division too.
        span = (
            (row.get("metadata") or {}).get("position_end") or row["position"]
        ) - row["position"]
        rows.append(
            dict(
                name=players.get(pid, {}).get("name", "Entrenador"),
                league=row["division_id"],
                position=row["division_position"],
                position_end=row["division_position"] + span,
                points=row["points_awarded"],
                coins=row["coins_awarded"],
                total=total,
                balance=balance[pid] if closed_at else None,
                status=players.get(pid, {}).get("status"),
            )
        )
    results = defaultdict(list)
    for m in snapshot["inputs"]["matches"]:
        a, b = (
            players.get(m["player_a_id"], {}).get("name", "?"),
            players.get(m["player_b_id"], {}).get("name", "?"),
        )
        winner = m.get("winner_id")
        results[m.get("division") or "A"].append(
            (a, b)
            if winner == m["player_a_id"]
            else (b, a)
            if winner == m["player_b_id"]
            else (None, f"{a} · {b}")
        )
    league_of = {row["trainer_id"]: row["division_id"] for row in standings}
    moves = []
    if not snapshot.get("final") and "B" in leagues:
        for code, target in (("A", "promotion"), ("B", "relegation")):
            for pid in (snapshot.get("new_divisions") or {}).get(code, []):
                if league_of.get(pid) and league_of[pid] != code:
                    moves.append(
                        (target, players.get(pid, {}).get("name", "Entrenador"))
                    )
    gift = snapshot.get("last_b_player_id")
    return dict(
        season=season["name"],
        matchday=day["number"],
        corrected=s["revision"] > 1,
        final=bool(snapshot.get("final")),
        leagues=leagues,
        rows=rows,
        results=dict(results),
        moves=moves,
        at=closed_at,
        gift=players.get(gift, {}).get("name") if gift else None,
    )


def _season_finished(f: Facts, s: dict) -> dict:
    final = one(
        f.read(
            "league_finalizations",
            "season_id,title,artifact,created_at",
            id=s["finalization_id"],
        )
    )
    season = f.season(final["season_id"])
    title, artifact = final["title"], final["artifact"]
    leagues = f.leagues(season["id"])
    roster = {r["id"]: r for r in artifact.get("roster", [])}
    names = {
        r["id"]: r.get("display_name") or "Entrenador"
        for r in artifact.get("roster", [])
    }
    champion = next(
        (
            p
            for p in title.get("players", [])
            if p.get("trainer_id") == title.get("champion_trainer_id")
        ),
        None,
    )
    if champion is None:
        raise Skip("champion_missing")
    coins = defaultdict(int)
    for day in artifact.get("rounds", []):
        for row in day.get("standings", []):
            coins[row["season_player_id"]] += int(row.get("coins_awarded") or 0)
    final_day = {
        r["season_player_id"]: r.get("division") for r in artifact.get("standings", [])
    }
    divisions = {
        d["id"]: d["code"]
        for d in f.read("divisions", "id,code", season_id=season["id"])
    }
    moves = []
    for m in artifact.get("movements", []):
        if m.get("type") in ("promotion", "relegation"):
            number_ = next(
                (
                    d["number"]
                    for d in artifact.get("rounds", [])
                    if d["id"] == m["matchday_id"]
                ),
                None,
            )
            moves.append(
                (
                    m["type"],
                    names.get(m["season_player_id"], "Entrenador"),
                    divisions.get(m.get("to_division_id")),
                    number_,
                )
            )
    standings = [
        dict(
            name=p.get("display_name")
            or names.get(p["season_player_id"], "Entrenador"),
            total=Decimal(str(p["total_points"])),
            coins=coins.get(p["season_player_id"], 0),
            league=final_day.get(p["season_player_id"]),
            status=roster.get(p["season_player_id"], {}).get("status"),
        )
        for p in title["players"]
    ]
    rounds = artifact.get("rounds", [])
    return dict(
        season=season["name"],
        champion=champion.get("display_name") or "Entrenador",
        champion_points=Decimal(str(champion["total_points"])),
        resolution=title.get("resolution_type"),
        standings=standings,
        leagues=leagues,
        moves=moves,
        team=(artifact.get("league") or {}).get("team") or [],
        matchdays=len(rounds),
        trainers=len(roster),
        at=instant(final["created_at"]),
    )


def _cup_sides(snapshot) -> dict[str, str]:
    return {
        s["id"]: s.get("name")
        or " / ".join(m.get("display_name", "?") for m in s.get("members", []))
        for s in snapshot.get("sides", [])
    }


def _cup_round(f: Facts, s: dict) -> dict:
    history = one(
        f.read(
            "cup_history",
            "cup_id,snapshot,created_at",
            cup_id=s["cup_id"],
            revision=s["revision"],
        )
    )
    snapshot = history["snapshot"]
    season = f.season(snapshot["season_id"])
    closed = [r for r in snapshot.get("rounds", []) if r.get("status") == "closed"]
    if not closed:
        raise Skip("round_missing")
    rnd = max(closed, key=lambda r: r["number"])
    sides = _cup_sides(snapshot)
    matches = []
    for m in rnd.get("matches", []):
        a, b = sides.get(m.get("a")), sides.get(m.get("b"))
        if a and not b or b and not a:
            matches.append(dict(bye=a or b))
        elif a and b:
            winner = m.get("winner")
            score = (
                f"{m['score_a']}-{m['score_b']}" if m.get("score_a") is not None else ""
            )
            matches.append(
                dict(
                    a=a,
                    b=b,
                    score=score,
                    winner=a
                    if winner == m.get("a")
                    else b
                    if winner == m.get("b")
                    else None,
                )
            )
    table = [
        dict(
            name=sides.get(t["side_id"], "?"),
            position=t["position"],
            wins=t["wins"],
            losses=t["losses"],
        )
        for t in snapshot.get("standings", [])
        if t.get("position")
    ]
    return dict(
        season=season["name"],
        cup=snapshot.get("name") or "Copa",
        round=rnd["number"],
        phase=rnd.get("phase"),
        matches=matches,
        table=table if rnd.get("phase") in ("swiss", "round_robin") else [],
        at=instant(history["created_at"]),
    )


def _cup_finished(f: Facts, s: dict) -> dict:
    cert = one(
        f.read(
            "cup_certificates",
            "season_id,champion_side_id,finalist_side_id,snapshot,certified_at",
            cup_id=s["cup_id"],
        )
    )
    season = f.season(cert["season_id"])
    snapshot = cert["snapshot"]
    sides = _cup_sides(snapshot)
    final = next(
        (
            m
            for r in snapshot.get("rounds", [])
            if r.get("phase") == "final"
            for m in r.get("matches", [])
            if m.get("winner") == cert["champion_side_id"]
        ),
        None,
    )
    score = ""
    if final and final.get("score_a") is not None:
        a, b = final["score_a"], final["score_b"]
        score = f"{max(a, b)}-{min(a, b)}"
    return dict(
        season=season["name"],
        cup=snapshot.get("name") or "Copa",
        doubles=snapshot.get("format") == "doubles",
        champion=sides.get(cert["champion_side_id"], "?"),
        finalist=sides.get(cert["finalist_side_id"], "?"),
        score=score,
        sides=len(sides),
        at=instant(cert["certified_at"]),
    )


def _robbery(f: Facts, s: dict) -> dict:
    r = one(
        f.read(
            "redemptions",
            "season_id,trainer_id,target_owner_trainer_id,target_pokemon_entity_id,identity_revision_id,effect_code,status,redeemed_at",
            id=s["redemption_id"],
        )
    )
    if r["effect_code"] != "steal" or r["status"] != "applied":
        raise Skip("not_a_robbery")
    season = f.season(r["season_id"])
    names = f.names([r["trainer_id"], r["target_owner_trainer_id"]])
    pokemon = None
    # The target was in the victim's public team (rival targets come only from
    # public team locks); read just that party slot of the observed save.
    seen = f.read(
        "pokemon_observations",
        "save_file_id,source,slot_number",
        revision_id=r["identity_revision_id"],
        pokemon_entity_id=r["target_pokemon_entity_id"],
    )
    if len(seen) == 1 and seen[0]["source"] == "party":
        for parsed in f.read(
            "parsed_saves",
            "status,party:payload->party",
            save_file_id=seen[0]["save_file_id"],
            status="parsed",
        ):
            for slot in parsed.get("party") or []:
                if (
                    isinstance(slot, dict)
                    and slot.get("slot_number") == seen[0]["slot_number"]
                    and isinstance(slot.get("pokemon"), dict)
                ):
                    pokemon = slot["pokemon"]
            if pokemon:
                break
    return dict(
        season=season["name"],
        robber=names.get(r["trainer_id"], "Entrenador"),
        victim=names.get(r["target_owner_trainer_id"], "Entrenador"),
        pokemon=pokemon if pokemon and pokemon.get("species") else None,
        at=instant(r["redeemed_at"]),
    )


def _trial(f: Facts, s: dict) -> dict:
    case = one(
        f.read(
            "trial_cases",
            "id,season_id,case_number,title,description,status,verdict,decision_revision_id,is_public:payload->>is_public",
            id=s["case_id"],
        )
    )
    if (
        str(case.get("is_public") or "true").lower() in ("false", "0", "no")
        or case["status"] == "cancelled"
    ):
        raise Skip("not_public")
    if case["decision_revision_id"] != s["revision_id"]:
        raise Skip("superseded")
    season = f.season(case["season_id"])
    revision = one(
        f.read("trial_case_revisions", "operation,created_at", id=s["revision_id"])
    )
    sanctions = f.read(
        "penalties",
        "penalty_type,amount,points_amount,duration_matchdays,start_matchday_number,end_matchday_number",
        trial_case_id=case["id"],
        trial_revision_id=s["revision_id"],
    )
    return dict(
        season=season["name"],
        number=case.get("case_number"),
        title=case["title"],
        description=case.get("description") or "",
        verdict=case["verdict"],
        corrected=revision["operation"] == "correct",
        sanctions=sanctions,
        at=instant(revision["created_at"]),
    )


def _participant_status(f: Facts, s: dict) -> dict:
    player = one(
        f.read(
            "season_players", "season_id,trainer_id,status", id=s["season_player_id"]
        )
    )
    if player["status"] != s["status"] or s["status"] not in STATUS_LABELS:
        raise Skip("status_changed")
    season = f.season(player["season_id"])
    return dict(
        season=season["name"],
        trainer=f.names([player["trainer_id"]]).get(player["trainer_id"], "Entrenador"),
        status=s["status"],
        matchday=s.get("matchday_number"),
    )


# -- embeds -----------------------------------------------------------------------


def _mon(m: dict) -> str:
    species = clean(m.get("species"), 40)
    nick = clean(m.get("nickname"), 24)
    label = (
        f"{nick} ({species})" if nick and nick.lower() != species.lower() else species
    )
    parts = [("✨ " if m.get("is_shiny") else "") + f"**{label}**"]
    if isinstance(m.get("level"), int):
        parts.append(f"Nv. {m['level']}")
    if m.get("item"):
        parts.append(f"@ {clean(m['item'], 32)}")
    return " · ".join(parts)


def render(facts: dict) -> dict:
    kind = facts["kind"]
    footer = f"PokeApp · {clean(facts.get('season'), 80)}"
    if kind == "season_started":
        lines = [
            f"**{clean(facts['season'], 80)}** ya está en marcha: {facts['players']} entrenadores, "
            f"{facts['total_matchdays']} jornadas.",
            "",
            "¡Que empiece la competición!",
        ]
        fields = []
        for league, names in facts["leagues"].items():
            fields += lines_fields(
                f"🗂️ {league} ({len(names)})",
                [f"• {clean(n)}" for n in names],
                inline=len(facts["leagues"]) > 1,
            )
        return embed(
            title="🏁 ¡Arranca la temporada!",
            description="\n".join(lines),
            color=LEAF,
            fields=fields,
            footer=footer,
        )
    if kind == "team_locked":
        lines = [
            f"**{clean(facts['trainer'])}** ha fijado su equipo para la **Jornada {facts['matchday']}**."
        ]
        if facts["late"]:
            lines.append("⏰ Fijado fuera de plazo.")
        if facts["revision"] > 1:
            lines.append("🔁 Equipo reemplazado mientras la jornada sigue abierta.")
        fields = lines_fields(
            "Equipo", [f"`{i}` {_mon(m)}" for i, m in enumerate(facts["team"], 1)]
        )
        fields.append(
            {
                "name": "Equipos fijados",
                "value": f"{facts['fixed']}/{facts['participants']}",
                "inline": True,
            }
        )
        return embed(
            title=f"🔒 Equipo fijado · Jornada {facts['matchday']}",
            description="\n".join(lines),
            color=WARM if facts["late"] else ACCENT,
            fields=fields,
            footer=footer,
            timestamp=facts["at"],
        )
    if kind in ("matchday_closed", "matchday_corrected"):
        return _render_matchday(facts, footer)
    if kind == "season_finished":
        return _render_season(facts, footer)
    if kind == "cup_round_closed":
        lines = []
        for m in facts["matches"]:
            if "bye" in m:
                lines.append(f"• **{clean(m['bye'])}** pasa sin rival")
            elif m["winner"]:
                loser = m["b"] if m["winner"] == m["a"] else m["a"]
                score = f" ({m['score']})" if m["score"] else ""
                lines.append(
                    f"• **{clean(m['winner'])}** vence a {clean(loser)}{score}"
                )
            else:
                lines.append(f"• {clean(m['a'])} · {clean(m['b'])}: sin resultado")
        fields = lines_fields("⚔️ Resultados", lines)
        if facts["table"]:
            fields += lines_fields(
                "📊 Clasificación",
                [
                    f"{medal(t['position'])} {clean(t['name'])} · {t['wins']}V {t['losses']}D"
                    for t in facts["table"]
                ],
            )
        phase = PHASES.get(facts["phase"], "Ronda")
        return embed(
            title=f"🏅 {clean(facts['cup'], 80)} · {phase} {facts['round']}",
            description=f"Ronda {facts['round']} cerrada: estos son los resultados.",
            color=VIOLET,
            fields=fields,
            footer=footer,
            timestamp=facts["at"],
        )
    if kind == "cup_finished":
        score = f" por **{facts['score']}**" if facts["score"] else ""
        desc = (
            f"👑 **{clean(facts['champion'])}** gana la copa{score} en la final ante **{clean(facts['finalist'])}**.\n\n"
            f"{facts['sides']} {'parejas' if facts['doubles'] else 'participantes'} · Ya en el Hall de la Fama."
        )
        return embed(
            title=f"🏆 {clean(facts['cup'], 80)} · ¡Final!",
            description=desc,
            color=GOLD,
            footer=footer,
            timestamp=facts["at"],
        )
    if kind == "robbery_completed":
        target = _mon(facts["pokemon"]) if facts["pokemon"] else "un Pokémon"
        desc = (
            f"**{clean(facts['robber'])}** le ha robado {target} a **{clean(facts['victim'])}**.\n"
            "El robo está confirmado y el Pokémon cambia de equipo."
        )
        return embed(
            title="🦹 ¡Robo Pokémon!",
            description=desc,
            color=MAGENTA,
            footer=footer,
            timestamp=facts["at"],
        )
    if kind == "trial_resolved":
        label = f"Caso {facts['number']}" if facts["number"] is not None else "Caso"
        guilty = facts["verdict"] == "guilty"
        desc = f"**{clean(facts['title'], 120)}**\n{clean(facts['description'], 600)}"
        sanctions = [_sanction(p) for p in facts["sanctions"]] or ["Sin sanciones."]
        fields = [
            {
                "name": "Veredicto",
                "value": "Culpable" if guilty else "No culpable",
                "inline": True,
            }
        ]
        fields += lines_fields("Sanciones", sanctions)
        heading = "Decisión corregida" if facts["corrected"] else "Decisión del juicio"
        return embed(
            title=f"⚖️ {heading} · {label}",
            description=desc,
            color=DANGER if guilty else MUTED,
            fields=fields,
            footer=footer,
            timestamp=facts["at"],
        )
    if kind == "participant_status":
        since = (
            f" desde la Jornada {facts['matchday']}" if facts.get("matchday") else ""
        )
        desc = (
            f"**{clean(facts['trainer'])}** {STATUS_LABELS[facts['status']]}{since}.\n"
            "Sus resultados anteriores se conservan; deja de contar para las próximas jornadas."
        )
        return embed(
            title="🚪 Cambio en la competición",
            description=desc,
            color=MUTED,
            footer=footer,
        )
    raise Skip("unknown_kind")


def _sanction(p: dict) -> str:
    kind = p["penalty_type"]
    if kind == "points_reduction":
        return f"• −{number(p.get('points_amount') or p.get('amount'))} puntos"
    if kind == "coins_reduction":
        return f"• −{number(p.get('amount'))} 🪙"
    if kind == "store_ban":
        start, end = p.get("start_matchday_number"), p.get("end_matchday_number")
        span = f"jornadas {start}–{end}" if start != end else f"jornada {start}"
        return f"• Sin tienda: {span}"
    if kind == "pokemon_release":
        return "• Liberación de un Pokémon"
    return "• Otra sanción (detalle en PokeApp)"


def _render_matchday(facts: dict, footer: str) -> dict:
    leagues = facts["leagues"]
    corrected = facts["corrected"]
    desc = [
        f"*{clean(facts['season'], 80)}* · {' y '.join(leagues.values()) or 'Liga'}"
    ]
    if facts["final"]:
        desc.append("🏁 Última jornada de la temporada.")
    if corrected:
        desc.append(
            "✏️ Resultados corregidos por la administración: estas son las cifras oficiales."
        )
    fields = []
    for code, label in leagues.items():
        lines = [
            f"• **{clean(w)}** vence a {clean(l)}"
            if w
            else f"• {clean(l)}: sin resultado"
            for w, l in facts["results"].get(code, [])
        ]
        if lines:
            fields += lines_fields(f"⚔️ Resultados · {label}", lines)
    for code, label in leagues.items():
        rows = sorted(
            (r for r in facts["rows"] if r["league"] == code),
            key=lambda r: (r["position"], r["name"].lower()),
        )
        lines = []
        for r in rows:
            place = (
                medal(r["position"])
                if r["position_end"] == r["position"]
                else f"{r['position']}–{r['position_end']}."
            )
            lines.append(
                f"{place} {clean(r['name'])} · {signed(r['points'])} pts · {signed(r['coins'])} 🪙"
            )
        if lines:
            fields += lines_fields(f"📊 Jornada {facts['matchday']} · {label}", lines)
    table = sorted(facts["rows"], key=lambda r: (-r["total"], r["name"].lower()))
    lines = []
    for place, r in zip(ranks([r["total"] for r in table]), table):
        balance = f" · {r['balance']} 🪙 saldo" if r["balance"] is not None else ""
        league = (
            f" ({leagues.get(r['league'], r['league'])})" if len(leagues) > 1 else ""
        )
        lines.append(
            f"{medal(place)} **{clean(r['name'])}**{league} — {number(r['total'])} pts{balance}"
        )
    fields += lines_fields("🏆 Clasificación general", lines)
    if facts["moves"]:
        ups = [clean(n) for t, n in facts["moves"] if t == "promotion"]
        downs = [clean(n) for t, n in facts["moves"] if t == "relegation"]
        lines = ([f"⬆️ Ascienden a Liga A: {', '.join(ups)}"] if ups else []) + (
            [f"⬇️ Descienden a Liga B: {', '.join(downs)}"] if downs else []
        )
        fields += lines_fields("🔄 Ascensos y descensos", lines)
    if facts["gift"]:
        fields.append(
            {
                "name": "🎁 Premio de consolación",
                "value": f"**{clean(facts['gift'])}**, último de Liga B, recibe un Robo Pokémon.",
                "inline": False,
            }
        )
    title = (
        f"✏️ Jornada {facts['matchday']} corregida"
        if corrected
        else f"📣 Jornada {facts['matchday']} finalizada"
    )
    return embed(
        title=title,
        description="\n".join(desc),
        color=VIOLET if corrected else INFO,
        fields=fields,
        footer=footer,
        timestamp=facts["at"],
    )


def _render_season(facts: dict, footer: str) -> dict:
    notes = {
        "championship_bo3": "El título se decidió en un desempate al mejor de tres.",
        "triple_adjusted_deaths": "Triple empate a puntos: decide el menor número de muertes ajustadas.",
        "championship_residual": "Empate resuelto por decisión de la administración.",
    }
    desc = [
        f"👑 **{clean(facts['champion'])}** gana **{clean(facts['season'], 80)}** con **{number(facts['champion_points'])} puntos**."
    ]
    if facts["resolution"] in notes:
        desc.append(notes[facts["resolution"]])
    desc.append(f"\n{facts['matchdays']} jornadas · {facts['trainers']} entrenadores.")
    leagues = facts["leagues"]
    table = facts["standings"]
    lines = []
    for place, r in zip(ranks([r["total"] for r in table]), table):
        league = (
            f" ({leagues.get(r['league'], r['league'])})"
            if len(leagues) > 1 and r["league"]
            else ""
        )
        lines.append(
            f"{medal(place)} **{clean(r['name'])}**{league} — {number(r['total'])} pts"
        )
    fields = lines_fields("📋 Clasificación final", lines)
    fields += lines_fields(
        "💰 Monedas ganadas en la temporada",
        [
            f"• {clean(r['name'])}: {r['coins']} 🪙"
            for r in sorted(table, key=lambda r: (-r["coins"], r["name"].lower()))
        ],
    )
    if facts["moves"]:
        fields += lines_fields(
            "🔄 Ascensos y descensos",
            [
                f"{'⬆️' if t == 'promotion' else '⬇️'} {n} → Liga {c}"
                + (f" (tras la J{d})" if d else "")
                for t, n, c, d in facts["moves"]
            ],
        )
    if facts["team"]:
        fields += lines_fields(
            "⭐ Equipo campeón",
            [
                f"• {_mon(m)}"
                for m in facts["team"]
                if isinstance(m, dict) and m.get("species")
            ],
        )
    return embed(
        title=f"🏆 Final de temporada · {clean(facts['season'], 80)}",
        description="\n".join(desc),
        color=GOLD,
        fields=fields,
        footer=footer,
        timestamp=facts["at"],
    )


TEST_PAYLOAD = embed(
    title="🔧 Prueba de conexión",
    description="Aaron Avisa! está conectado a PokeApp.\nEste mensaje es solo una prueba: no es un anuncio de la competición.",
    color=MUTED,
)


# -- delivery ---------------------------------------------------------------------


@dataclass
class Dispatcher:
    """Delivers due announcements; one instance, one thread."""

    outbox: object
    read: object
    webhook: object
    now: object = lambda: datetime.now(UTC)
    paused_until: datetime | None = None

    def run_once(self) -> float | None:
        """Deliver what is due. Seconds until the next due row, or None when idle."""
        now = self.now()
        if self.paused_until and now < self.paused_until:
            return (self.paused_until - now).total_seconds()
        self.outbox.recover(now - LEASE)
        self.outbox.expire(now - MAX_AGE)
        for row in self.outbox.due(now, BATCH):
            wait = self.webhook.ready_in()
            if wait > 30:
                return wait
            if not self._deliver(row):
                break
        upcoming = self.outbox.next_due()
        if upcoming is None:
            return None
        return max(1.0, (upcoming - self.now()).total_seconds())

    def _deliver(self, row: dict) -> bool:
        edit = row["status"] == "sent"
        claimed = self.outbox.claim(row, self.now())
        if claimed is None:
            return True
        rid, revision = claimed["id"], claimed["revision"]
        try:
            facts = gather(
                claimed["kind"], claimed["subject"], self.read, revision=revision
            )
            payload = render(facts)
        except Skip as skip:
            logger.info(
                "discord_announcement id=%s kind=%s skipped=%s",
                rid,
                claimed["kind"],
                skip.code,
            )
            self._close(claimed, edit, "skipped", skip.code)
            return True
        except PersistenceError:
            self._retry(claimed, edit, "facts_unavailable", 0)
            return True
        except (
            KeyError,
            TypeError,
            ValueError,
            AttributeError,
            InvalidOperation,
        ) as error:
            # Malformed source: retrying cannot change it.
            logger.warning(
                "discord_announcement id=%s kind=%s invalid=%s",
                rid,
                claimed["kind"],
                type(error).__name__,
            )
            self._close(claimed, edit, "failed", "facts_invalid")
            return True
        outcome = (
            self.webhook.edit(claimed["discord_message_id"], payload)
            if edit
            else self.webhook.post(payload)
        )
        logger.info(
            "discord_announcement id=%s kind=%s edit=%s outcome=%s",
            rid,
            claimed["kind"],
            edit,
            outcome.code,
        )
        if outcome.result == "delivered":
            fields = dict(
                status="sent", delivered_revision=revision, attempts=0, last_error=None
            )
            if not edit:
                fields.update(
                    sent_at=self.now().isoformat(),
                    discord_message_id=outcome.message_id,
                )
            self.outbox.update(claimed, fields)
        elif outcome.result == "retry" or (edit and outcome.result == "uncertain"):
            self._retry(claimed, edit, outcome.code, outcome.retry_after)
            if outcome.code == "webhook_rejected":
                self.paused_until = self.now() + timedelta(seconds=outcome.retry_after)
                return False
        elif outcome.result == "uncertain":
            # Discord may already show it: never post it again.
            self.outbox.update(
                claimed, dict(status="uncertain", last_error=outcome.code)
            )
        else:
            self._close(claimed, edit, "failed", outcome.code)
        return True

    def _close(self, row, edit, status, code):
        if edit:  # keep the message as it is; stop editing it
            self.outbox.update(
                row,
                dict(
                    status="sent", delivered_revision=row["revision"], last_error=code
                ),
            )
        else:
            self.outbox.update(row, dict(status=status, last_error=code))

    def _retry(self, row, edit, code, retry_after):
        attempts = row["attempts"]
        if attempts >= MAX_ATTEMPTS:
            self._close(row, edit, "failed", code)
            return
        delay = max(
            BACKOFF_SECONDS[min(attempts, len(BACKOFF_SECONDS)) - 1], retry_after
        )
        self.outbox.update(
            row,
            dict(
                status="sent" if edit else "pending",
                last_error=code,
                next_attempt_at=(self.now() + timedelta(seconds=delay)).isoformat(),
            ),
        )
