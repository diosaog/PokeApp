"""Owner decision (2026-10-26): every trainer has Rare Candy and Heart Scale ∞.

Virtual, permanent and free: never stored as a quantity, never purchased,
consumed or charged, identical for existing and new trainers in every season.
Each physical addition still respects the game's real bag limits.
"""

UNLIMITED_ITEMS = (
    {
        "code": "rare_candy",
        "item_id": 50,
        "name": "Rare Candy",
        "label": "Caramelo Raro",
        "description": "Sube un nivel a un Pokémon. Gratis e ilimitado: añádelos a tu partida desde PokeApp Launcher.",
    },
    {
        "code": "heart_scale",
        "item_id": 93,
        "name": "Heart Scale",
        "label": "Escama Corazón",
        "description": "Permite recordar movimientos. Gratis e ilimitada: añádelas a tu partida desde PokeApp Launcher.",
    },
)
