from __future__ import annotations

JUICIOS_STATE_KEY = "juicios_state_v1"

STATUS_ORDER = ["abierto", "en_revision", "resuelto", "cancelado"]
STATUS_LABELS = {
    "abierto": "Abierto",
    "en_revision": "En revision",
    "resuelto": "Resuelto",
    "cancelado": "Cancelado",
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

