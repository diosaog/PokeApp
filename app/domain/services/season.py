from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from app.domain.seasons import SeasonRules, SeasonVersion


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    title: str
    body: str


@dataclass(frozen=True)
class VersionApplicationDecision:
    allowed: bool
    reason: str = "ok"
    minimum_matchday: int = 1


def _issue(level: str, title: str, body: str) -> ValidationIssue:
    return ValidationIssue(level=level, title=title, body=body)


def _clean_ids(values: Iterable[Any]) -> tuple[str, ...]:
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if text and text not in out:
            out.append(text)
    return tuple(out)


def select_effective_version(
    versions: Iterable[SeasonVersion],
    *,
    matchday_number: int | None = None,
    active_version_id: str = "",
) -> SeasonVersion:
    ordered = sorted(
        list(versions),
        key=lambda version: (int(version.effective_matchday), str(version.id)),
    )
    if not ordered:
        raise ValueError("At least one season version is required.")
    if matchday_number is None:
        active = str(active_version_id or "").strip()
        for version in reversed(ordered):
            if version.id == active:
                return version
        return ordered[-1]
    target = max(1, int(matchday_number or 1))
    selected = ordered[0]
    for version in ordered:
        if int(version.effective_matchday) <= target:
            selected = version
            continue
        break
    return selected


def can_apply_version(
    *,
    effective_matchday: int,
    closed_matchdays: Iterable[int] = (),
    current_matchday: int = 1,
    matchday_is_open: bool = False,
) -> VersionApplicationDecision:
    effective = max(1, int(effective_matchday or 1))
    closed = sorted({int(value) for value in closed_matchdays if int(value) > 0})
    latest_closed = max(closed) if closed else 0
    if latest_closed and effective <= latest_closed:
        return VersionApplicationDecision(
            allowed=False,
            reason="closed_matchday",
            minimum_matchday=latest_closed + 1,
        )
    current = max(1, int(current_matchday or 1))
    if matchday_is_open and effective <= current:
        return VersionApplicationDecision(
            allowed=False,
            reason="open_matchday",
            minimum_matchday=current + 1,
        )
    return VersionApplicationDecision(allowed=True, minimum_matchday=effective)


def validate_season_version(
    version: SeasonVersion,
    *,
    known_trainers: Iterable[str] | None = None,
    supported_division_count: int = 2,
) -> tuple[ValidationIssue, ...]:
    issues: list[ValidationIssue] = []
    participants = _clean_ids(version.participant_ids)
    player_count = len(participants)
    division_sizes = tuple(int(size) for size in version.division_sizes)
    division_count = len(division_sizes)
    movement = int(version.promotion_relegation_count)

    if not participants:
        issues.append(_issue("error", "Sin jugadores", "La temporada necesita al menos 1 entrenador."))

    if len({name.casefold() for name in participants}) != len(participants):
        issues.append(_issue("error", "Jugadores repetidos", "Cada entrenador solo puede aparecer una vez."))

    if known_trainers is not None:
        known = {str(name or "").strip().casefold() for name in known_trainers}
        unknown = sorted(name for name in participants if name.casefold() not in known)
        if unknown:
            issues.append(
                _issue(
                    "error",
                    "Jugadores no registrados",
                    "No existen en el registro: " + ", ".join(unknown),
                )
            )

    if int(version.effective_matchday) > int(version.max_matchdays):
        issues.append(
            _issue(
                "error",
                "Tramo fuera de temporada",
                "El tramo de aplicacion no puede ser posterior a la ultima jornada.",
            )
        )

    if division_count != int(supported_division_count):
        issues.append(
            _issue(
                "error",
                "Divisiones no soportadas",
                "La version actual soporta oficialmente Liga A y Liga B.",
            )
        )

    if any(size <= 0 for size in division_sizes):
        issues.append(_issue("error", "Division vacia", "Todas las divisiones configuradas deben tener jugadores."))

    if player_count and sum(division_sizes) != player_count:
        issues.append(
            _issue(
                "error",
                "Reparto descuadrado",
                f"Las divisiones suman {sum(division_sizes)}, pero hay {player_count} jugadores.",
            )
        )

    if division_sizes:
        movement_cap = min(division_sizes[:2]) if len(division_sizes) >= 2 else 0
        if movement > movement_cap:
            first = division_sizes[0]
            second = division_sizes[1] if len(division_sizes) > 1 else 0
            issues.append(
                _issue(
                    "error",
                    "Ascensos imposibles",
                    f"No pueden moverse {movement} jugadores con ligas de {first} y {second}.",
                )
            )

    expected_positions = set(range(1, player_count + 1))
    point_positions = {int(pos) for pos in version.points_by_position}
    coin_positions = {int(pos) for pos in version.coins_by_position}
    missing_points = sorted(expected_positions - point_positions)
    missing_coins = sorted(expected_positions - coin_positions)
    if missing_points:
        issues.append(
            _issue(
                "error",
                "Puntos incompletos",
                "Faltan posiciones: " + ", ".join(str(pos) for pos in missing_points),
            )
        )
    if missing_coins:
        issues.append(
            _issue(
                "error",
                "Monedas incompletas",
                "Faltan posiciones: " + ", ".join(str(pos) for pos in missing_coins),
            )
        )

    extra_points = sorted(point_positions - expected_positions)
    extra_coins = sorted(coin_positions - expected_positions)
    if extra_points or extra_coins:
        issues.append(
            _issue(
                "warn",
                "Recompensas sobrantes",
                "Hay posiciones configuradas fuera del roster activo; no se usaran.",
            )
        )

    if not isinstance(version.rules, SeasonRules):
        issues.append(_issue("error", "Reglas invalidas", "Las reglas deben usar SeasonRules."))

    if not issues:
        issues.append(_issue("ok", "Configuracion lista", "La version se puede guardar sin bloquear la liga."))
    return tuple(issues)


def has_blocking_issues(issues: Iterable[ValidationIssue]) -> bool:
    return any(issue.level == "error" for issue in issues)


def season_version_changes(
    current: SeasonVersion,
    proposed: SeasonVersion,
) -> tuple[tuple[str, str, str], ...]:
    checks: list[tuple[str, Any, Any]] = [
        ("Nombre", current.name, proposed.name),
        ("Aplicar desde", current.effective_matchday, proposed.effective_matchday),
        ("Jornadas", current.max_matchdays, proposed.max_matchdays),
        ("Jugadores", current.participant_ids, proposed.participant_ids),
        ("Divisiones", current.division_sizes, proposed.division_sizes),
        ("Ascensos/descensos", current.promotion_relegation_count, proposed.promotion_relegation_count),
        ("Puntos", current.points_by_position, proposed.points_by_position),
        ("Monedas", current.coins_by_position, proposed.coins_by_position),
        ("Reglas", current.rules, proposed.rules),
    ]
    return tuple((label, str(before), str(after)) for label, before, after in checks if before != after)
