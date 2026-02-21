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

VERDICT_PENDING = "pendiente"
VERDICT_GUILTY = "culpable"
VERDICT_NOT_GUILTY = "no_culpable"

VERDICT_ORDER = [VERDICT_PENDING, VERDICT_GUILTY, VERDICT_NOT_GUILTY]
VERDICT_LABELS = {
    VERDICT_PENDING: "Pendiente",
    VERDICT_GUILTY: "Culpable",
    VERDICT_NOT_GUILTY: "No culpable",
}

VOTE_GUILTY = "culpable"
VOTE_NOT_GUILTY = "no_culpable"
VOTE_ORDER = [VOTE_GUILTY, VOTE_NOT_GUILTY]
VOTE_LABELS = {
    VOTE_GUILTY: "Culpable",
    VOTE_NOT_GUILTY: "No culpable",
}

PENALTY_TEMPLATE_FIRST = "primera_falta"
PENALTY_TEMPLATE_REPEAT = "reincidencia"
PENALTY_TEMPLATE_SEVERE = "grave"

PENALTY_TEMPLATE_ORDER = [
    PENALTY_TEMPLATE_FIRST,
    PENALTY_TEMPLATE_REPEAT,
    PENALTY_TEMPLATE_SEVERE,
]
PENALTY_TEMPLATE_LABELS = {
    PENALTY_TEMPLATE_FIRST: "Primera falta",
    PENALTY_TEMPLATE_REPEAT: "Reincidencia",
    PENALTY_TEMPLATE_SEVERE: "Grave",
}

PENALTY_TEMPLATES = {
    PENALTY_TEMPLATE_FIRST: [
        {"type": PENALTY_POINTS_REDUCTION, "amount": 1.0},
    ],
    PENALTY_TEMPLATE_REPEAT: [
        {"type": PENALTY_COINS_REDUCTION, "amount": 12},
        {"type": PENALTY_POINTS_REDUCTION, "amount": 2.0},
        {"type": PENALTY_STORE_BAN},
    ],
    PENALTY_TEMPLATE_SEVERE: [
        {"type": PENALTY_COINS_REDUCTION, "amount": 20},
        {"type": PENALTY_POINTS_REDUCTION, "amount": 4.0},
        {"type": PENALTY_STORE_BAN},
        {"type": PENALTY_POKEMON_RELEASE, "text": "Liberar 1 Pokemon (definir especie)"},
    ],
}
