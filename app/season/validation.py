from __future__ import annotations

from typing import Any

from app.season.config import SeasonVersion


Issue = dict[str, str]


def _issue(level: str, title: str, body: str) -> Issue:
    return {"level": level, "title": title, "body": body}


def validate_season_version(version: SeasonVersion) -> list[Issue]:
    issues: list[Issue] = []
    players = [str(player).strip() for player in version.players if str(player).strip()]
    player_count = len(players)
    division_sizes = [int(size or 0) for size in version.division_sizes]

    if not players:
        issues.append(_issue("error", "Sin jugadores", "La temporada necesita al menos 1 entrenador."))

    if len(set(name.lower() for name in players)) != len(players):
        issues.append(_issue("error", "Jugadores repetidos", "Cada entrenador solo puede aparecer una vez."))

    if int(version.max_rounds or 0) < 1:
        issues.append(_issue("error", "Jornadas invalidas", "La liga necesita al menos 1 jornada."))

    if int(version.effective_round or 0) > int(version.max_rounds or 0):
        issues.append(
            _issue(
                "error",
                "Tramo fuera de temporada",
                "El tramo de aplicacion no puede ser posterior a la ultima jornada.",
            )
        )

    if int(version.division_count or 0) != len(division_sizes):
        issues.append(_issue("error", "Divisiones incompletas", "El numero de ligas no coincide con sus tamanos."))

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

    if len(division_sizes) >= 2:
        movement_cap = min(division_sizes[0], division_sizes[1])
        if int(version.movement_count or 0) > movement_cap:
            issues.append(
                _issue(
                    "error",
                    "Ascensos imposibles",
                    f"No pueden moverse {int(version.movement_count)} jugadores con ligas de {division_sizes[0]} y {division_sizes[1]}.",
                )
            )
    elif int(version.movement_count or 0) > 0:
        issues.append(_issue("warn", "Sin segunda liga", "Los ascensos no tienen efecto con una sola division."))

    expected_positions = set(range(1, player_count + 1))
    point_positions = set(int(pos) for pos in version.points_by_position)
    coin_positions = set(int(pos) for pos in version.coins_by_position)
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

    if not issues:
        issues.append(_issue("ok", "Configuracion lista", "La version se puede guardar sin bloquear la liga."))
    return issues


def has_blocking_issues(issues: list[Issue]) -> bool:
    return any(issue.get("level") == "error" for issue in issues)


def season_version_changes(current: SeasonVersion, proposed: SeasonVersion) -> list[tuple[str, str, str]]:
    checks: list[tuple[str, Any, Any]] = [
        ("Nombre", current.name, proposed.name),
        ("Aplicar desde", current.effective_round, proposed.effective_round),
        ("Jornadas", current.max_rounds, proposed.max_rounds),
        ("Jugadores", current.players, proposed.players),
        ("Divisiones", current.division_sizes, proposed.division_sizes),
        ("Ascensos/descensos", current.movement_count, proposed.movement_count),
        ("Puntos", current.points_by_position, proposed.points_by_position),
        ("Monedas", current.coins_by_position, proposed.coins_by_position),
    ]
    changes: list[tuple[str, str, str]] = []
    for label, before, after in checks:
        if before != after:
            changes.append((label, str(before), str(after)))
    return changes
