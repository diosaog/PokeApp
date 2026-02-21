from __future__ import annotations

JUICIOS_STATE_KEY = "juicios_state_v1"

STATUS_PROPOSED = "propuesto"
STATUS_IN_PROGRESS = "en_proceso"
STATUS_FINISHED = "finalizado"

STATUS_ORDER = [STATUS_PROPOSED, STATUS_IN_PROGRESS, STATUS_FINISHED]
STATUS_LABELS = {
    STATUS_PROPOSED: "Propuesto",
    STATUS_IN_PROGRESS: "En proceso",
    STATUS_FINISHED: "Finalizado",
}
STATUS_COLORS = {
    STATUS_PROPOSED: "#1f9d55",
    STATUS_IN_PROGRESS: "#d9822b",
    STATUS_FINISHED: "#c23030",
}
LEGACY_STATUS_MAP = {
    "abierto": STATUS_PROPOSED,
    "en_revision": STATUS_IN_PROGRESS,
    "resuelto": STATUS_FINISHED,
    "cancelado": STATUS_FINISHED,
}

PENALTY_STORE_BAN = "store_ban"
PENALTY_COINS_REDUCTION = "coins_reduction"
PENALTY_POKEMON_RELEASE = "pokemon_release"
PENALTY_POINTS_REDUCTION = "points_reduction"
PENALTY_OTHER = "other"

PENALTY_ORDER = [
    PENALTY_STORE_BAN,
    PENALTY_COINS_REDUCTION,
    PENALTY_POKEMON_RELEASE,
    PENALTY_POINTS_REDUCTION,
    PENALTY_OTHER,
]

PENALTY_LABELS = {
    PENALTY_STORE_BAN: "NO poder usar la tienda ni las monedas",
    PENALTY_COINS_REDUCTION: "Reduccion de monedas",
    PENALTY_POKEMON_RELEASE: "Liberacion / Muerte de un Pokemon",
    PENALTY_POINTS_REDUCTION: "Reduccion de puntos",
    PENALTY_OTHER: "Otro",
}
