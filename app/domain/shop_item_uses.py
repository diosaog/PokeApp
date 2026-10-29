"""How each Shop item is used (owner decision 2026-10-29).

- `pokemon`: redeemed in PokeApp on a Pokémon (Blindar, Revivir, Robar and the
  robbery shield voucher), unchanged.
- `bag`: an in-game object. PokeApp Launcher adds it to the bag of the
  trainer's league save through the native, journaled writer that «Objetos ∞»
  uses, and the server spends the purchase exactly once.
- `choice`: the same, after choosing which object of the family (Fósil,
  Objeto Evolutivo, Objeto Potenciador de Tipo, Gemas Elementales).
- `permission`: no object exists (Captura Extra): using it records the use.
- `unavailable`: no Gen 6/7 game has the object (Menta de Naturaleza: mints
  arrived in Gen 8); it is not sold and its purchases can be refunded.

Compatibility comes from the native writer's own pouch tables, read on X…UM
saves (its --shop-item-checks gate): Bottle Caps and the Ice Stone exist only
in Sun/Moon/Ultra Sun/Ultra Moon, every other object here in all eight games. Each code delivers
the object its image and description show; three catalog names are another
object's Spanish name («Baya Ziuela» is described and drawn as the Chesto
Berry, «Baya Atania» as the Persim Berry, «Lupa» as the Zoom Lens), and the
object described is the one delivered (its in-game name is shown).
"""

GEN6 = ("X", "Y", "OR", "AS")
GEN7 = ("SN", "MN", "US", "UM")
GAMES = GEN6 + GEN7
GAME_LABELS = {
    "X": "Pokémon X",
    "Y": "Pokémon Y",
    "OR": "Pokémon Rubí Omega",
    "AS": "Pokémon Zafiro Alfa",
    "SN": "Pokémon Sol",
    "MN": "Pokémon Luna",
    "US": "Pokémon Ultrasol",
    "UM": "Pokémon Ultraluna",
}

# code -> (game item id, in-game Spanish name). All Gen 6/7 unless listed in
# GEN7_ONLY. The native writer accepts exactly these codes.
BAG_ITEMS = {
    # Berries
    "cheri_berry": (149, "Baya Zreza"),
    "chesto_berry": (150, "Baya Atania"),
    "pecha_berry": (151, "Baya Meloc"),
    "rawst_berry": (152, "Baya Safre"),
    "aspear_berry": (153, "Baya Perasi"),
    "oran_berry": (155, "Baya Aranja"),
    "persim_berry": (156, "Baya Caquic"),
    "sitrus_berry": (158, "Baya Zidra"),
    "occa_berry": (184, "Baya Caoca"),
    "passho_berry": (185, "Baya Pasio"),
    "wacan_berry": (186, "Baya Gualot"),
    "rindo_berry": (187, "Baya Tamar"),
    "yache_berry": (188, "Baya Rimoya"),
    "chople_berry": (189, "Baya Pomaro"),
    "kebia_berry": (190, "Baya Kebia"),
    "shuca_berry": (191, "Baya Acardo"),
    "coba_berry": (192, "Baya Kouba"),
    "payapa_berry": (193, "Baya Payapa"),
    "tanga_berry": (194, "Baya Yecana"),
    "charti_berry": (195, "Baya Alcho"),
    "kasib_berry": (196, "Baya Drasi"),
    "haban_berry": (197, "Baya Anjiro"),
    "colbur_berry": (198, "Baya Dillo"),
    "babiri_berry": (199, "Baya Baribá"),
    "chilan_berry": (200, "Baya Chilan"),
    "liechi_berry": (201, "Baya Lichi"),
    "ganlon_berry": (202, "Baya Gonlan"),
    "salac_berry": (203, "Baya Aslac"),
    "petaya_berry": (204, "Baya Yapati"),
    "apicot_berry": (205, "Baya Aricoc"),
    "lansat_berry": (206, "Baya Zonlan"),
    "starf_berry": (207, "Baya Arabol"),
    # Held items
    "choice_specs": (297, "Gafas Elección"),
    "choice_band": (220, "Cinta Elección"),
    "choice_scarf": (287, "Pañuelo Elección"),
    "leftovers": (234, "Restos"),
    "focus_sash": (275, "Banda Aguante"),
    "life_orb": (270, "Vidasfera"),
    "eviolite": (538, "Mineral Evolutivo"),
    "rocky_helmet": (540, "Casco Dentado"),
    "air_balloon": (541, "Globo Helio"),
    "eject_button": (547, "Botón Escape"),
    "red_card": (542, "Tarjeta Roja"),
    "white_herb": (214, "Hierba Blanca"),
    "kings_rock": (221, "Roca del Rey"),
    "scope_lens": (232, "Periscopio"),
    "zoom_lens": (276, "Telescopio"),
    "toxic_orb": (272, "Toxisfera"),
    "flame_orb": (273, "Llamasfera"),
    # Gems
    "fire_gem": (548, "Gema Fuego"),
    "water_gem": (549, "Gema Agua"),
    "electric_gem": (550, "Gema Eléctrico"),
    "grass_gem": (551, "Gema Planta"),
    "ice_gem": (552, "Gema Hielo"),
    "fighting_gem": (553, "Gema Lucha"),
    "poison_gem": (554, "Gema Veneno"),
    "ground_gem": (555, "Gema Tierra"),
    "flying_gem": (556, "Gema Volador"),
    "psychic_gem": (557, "Gema Psíquico"),
    "bug_gem": (558, "Gema Bicho"),
    "rock_gem": (559, "Gema Roca"),
    "ghost_gem": (560, "Gema Fantasma"),
    "dragon_gem": (561, "Gema Dragón"),
    "dark_gem": (562, "Gema Siniestro"),
    "steel_gem": (563, "Gema Acero"),
    "normal_gem": (564, "Gema Normal"),
    "fairy_gem": (715, "Gema Hada"),
    # Type-boosting held items (Pixie Plate is the Fairy one)
    "silk_scarf": (251, "Pañuelo de Seda"),
    "charcoal": (249, "Carbón"),
    "mystic_water": (243, "Agua Mística"),
    "magnet": (242, "Imán"),
    "miracle_seed": (239, "Semilla Milagro"),
    "never_melt_ice": (246, "Antiderretir"),
    "black_belt": (241, "Cinturón Negro"),
    "poison_barb": (245, "Flecha Venenosa"),
    "soft_sand": (237, "Arena Fina"),
    "sharp_beak": (244, "Pico Afilado"),
    "twisted_spoon": (248, "Cuchara Torcida"),
    "silver_powder": (222, "Polvo Plata"),
    "hard_stone": (238, "Piedra Dura"),
    "spell_tag": (247, "Hechizo"),
    "dragon_fang": (250, "Colmillo Dragón"),
    "black_glasses": (240, "Gafas de Sol"),
    "metal_coat": (233, "Revest. Metálico"),
    "pixie_plate": (644, "Tabla Duende"),
    # Training
    "ability_capsule": (645, "Cápsula Habilidad"),
    "bottle_cap": (795, "Chapa Plateada"),
    "gold_bottle_cap": (796, "Chapa Dorada"),
    # Evolution
    "sun_stone": (80, "Piedra Solar"),
    "moon_stone": (81, "Piedra Lunar"),
    "fire_stone": (82, "Piedra Fuego"),
    "thunder_stone": (83, "Piedra Trueno"),
    "water_stone": (84, "Piedra Agua"),
    "leaf_stone": (85, "Piedra Hoja"),
    "shiny_stone": (107, "Piedra Día"),
    "dusk_stone": (108, "Piedra Noche"),
    "dawn_stone": (109, "Piedra Alba"),
    "ice_stone": (849, "Piedra Hielo"),
    "oval_stone": (110, "Piedra Oval"),
    "dragon_scale": (235, "Escama Dragón"),
    "upgrade": (252, "Mejora"),
    "protector": (321, "Protector"),
    "electirizer": (322, "Electrizador"),
    "magmarizer": (323, "Magmatizador"),
    "dubious_disc": (324, "Disco Extraño"),
    "reaper_cloth": (325, "Tela Terrible"),
    "razor_claw": (326, "Garra Afilada"),
    "razor_fang": (327, "Colmillo Agudo"),
    "deep_sea_tooth": (226, "Diente Marino"),
    "deep_sea_scale": (227, "Escama Marina"),
    "prism_scale": (537, "Escama Bella"),
    "whipped_dream": (646, "Dulce de Nata"),
    "sachet": (647, "Saquito Fragante"),
    # Fossils
    "root_fossil": (99, "Fósil Raíz"),
    "claw_fossil": (100, "Fósil Garra"),
    "helix_fossil": (101, "Fósil Hélix"),
    "dome_fossil": (102, "Fósil Domo"),
    "old_amber": (103, "Ámbar Viejo"),
    "armor_fossil": (104, "Fósil Coraza"),
    "skull_fossil": (105, "Fósil Cráneo"),
    "cover_fossil": (572, "Fósil Tapa"),
    "plume_fossil": (573, "Fósil Pluma"),
    "jaw_fossil": (710, "Fósil Mandíbula"),
    "sail_fossil": (711, "Fósil Aleta"),
}
GEN7_ONLY = frozenset({"bottle_cap", "gold_bottle_cap", "ice_stone"})

_GEMS = tuple(code for code in BAG_ITEMS if code.endswith("_gem"))
_BOOSTERS = (
    "silk_scarf", "charcoal", "mystic_water", "magnet", "miracle_seed",
    "never_melt_ice", "black_belt", "poison_barb", "soft_sand", "sharp_beak",
    "twisted_spoon", "silver_powder", "hard_stone", "spell_tag", "dragon_fang",
    "black_glasses", "metal_coat", "pixie_plate",
)  # fmt: skip
_EVOLUTION = (
    "fire_stone", "water_stone", "thunder_stone", "leaf_stone", "moon_stone",
    "sun_stone", "shiny_stone", "dusk_stone", "dawn_stone", "ice_stone",
    "oval_stone", "kings_rock", "metal_coat", "dragon_scale", "upgrade",
    "protector", "electirizer", "magmarizer", "dubious_disc", "reaper_cloth",
    "razor_claw", "razor_fang", "deep_sea_tooth", "deep_sea_scale",
    "prism_scale", "whipped_dream", "sachet",
)  # fmt: skip
_FOSSILS = (
    "helix_fossil", "dome_fossil", "old_amber", "root_fossil", "claw_fossil",
    "skull_fossil", "armor_fossil", "cover_fossil", "plume_fossil",
    "jaw_fossil", "sail_fossil",
)  # fmt: skip

POKEMON_ITEMS = ("blindar_pokemon", "revivir_pokemon", "robar_pokemon", "robbery_shield_voucher")
# Shop item code -> how it is used. Single objects deliver one code.
SHOP_USES = {
    **{code: {"mode": "pokemon"} for code in POKEMON_ITEMS},
    "captura_extra": {"mode": "permission"},
    "menta_naturaleza": {"mode": "unavailable"},
    "fosil": {"mode": "choice", "items": _FOSSILS},
    "gemas_elementales": {"mode": "choice", "items": _GEMS},
    "objeto_potenciador_tipo": {"mode": "choice", "items": _BOOSTERS},
    "objeto_evolutivo": {"mode": "choice", "items": _EVOLUTION},
    "capsula_habilidad": {"mode": "bag", "items": ("ability_capsule",)},
    "chapa_plateada": {"mode": "bag", "items": ("bottle_cap",)},
    "chapa_dorada": {"mode": "bag", "items": ("gold_bottle_cap",)},
    **{
        shop: {"mode": "bag", "items": (bag,)}
        for shop, bag in {
            "baya_aranja": "oran_berry",
            "baya_zidra": "sitrus_berry",
            "baya_zreza": "cheri_berry",
            "baya_ziuela": "chesto_berry",
            "baya_meloc": "pecha_berry",
            "baya_safre": "rawst_berry",
            "baya_perasi": "aspear_berry",
            "baya_atania": "persim_berry",
            "baya_aslac": "salac_berry",
            "baya_lichi": "liechi_berry",
            "baya_petaya": "petaya_berry",
            "baya_ganlon": "ganlon_berry",
            "baya_apicot": "apicot_berry",
            "baya_lansat": "lansat_berry",
            "baya_starf": "starf_berry",
            "baya_occa": "occa_berry",
            "baya_passho": "passho_berry",
            "baya_wacan": "wacan_berry",
            "baya_rindo": "rindo_berry",
            "baya_yache": "yache_berry",
            "baya_shuca": "shuca_berry",
            "baya_chople": "chople_berry",
            "baya_kebia": "kebia_berry",
            "baya_coba": "coba_berry",
            "baya_payapa": "payapa_berry",
            "baya_tanga": "tanga_berry",
            "baya_charti": "charti_berry",
            "baya_kasib": "kasib_berry",
            "baya_haban": "haban_berry",
            "baya_colbur": "colbur_berry",
            "baya_babiri": "babiri_berry",
            "baya_chilan": "chilan_berry",
            "gafas_elegidas": "choice_specs",
            "cinta_elegida": "choice_band",
            "panuelo_elegido": "choice_scarf",
            "restos": "leftovers",
            "banda_focus": "focus_sash",
            "vidasfera": "life_orb",
            "mineral_evolutivo": "eviolite",
            "casco_dentado": "rocky_helmet",
            "globo_helio": "air_balloon",
            "boton_escape": "eject_button",
            "tarjeta_roja": "red_card",
            "hierba_blanca": "white_herb",
            "roca_del_rey": "kings_rock",
            "periscopio": "scope_lens",
            "lupa": "zoom_lens",
            "toxisfera": "toxic_orb",
            "llamasfera": "flame_orb",
        }.items()
    },
}


def item_games(bag_code):
    """Games whose bag can hold this object (the native pouch tables)."""
    if bag_code not in BAG_ITEMS:
        return ()
    return GEN7 if bag_code in GEN7_ONLY else GAMES


def use_of(shop_code):
    """{"mode", "items", "games"}; an unknown code (an item added later by an
    administrator) has no use defined in PokeApp yet."""
    use = SHOP_USES.get(shop_code, {"mode": "unknown"})
    items = tuple(use.get("items", ()))
    if use["mode"] in ("bag", "choice"):
        games = tuple(g for g in GAMES if any(g in item_games(i) for i in items))
    elif use["mode"] in ("pokemon", "permission"):
        games = GAMES
    else:
        games = ()
    return {"mode": use["mode"], "items": items, "games": games}


def deliverable(shop_code, game):
    """Objects of this purchase that the bag of `game` can hold."""
    use = use_of(shop_code)
    if use["mode"] not in ("bag", "choice"):
        return ()
    return tuple(i for i in use["items"] if game in item_games(i))


def purchase_refusal(shop_code, league_game):
    """Why this item must not be sold to this trainer now, or None. An unknown
    league game (no save accepted yet) cannot refuse a compatible-somewhere
    item; delivery checks the real save later."""
    use = use_of(shop_code)
    if use["mode"] == "unavailable":
        return "ITEM_NOT_USABLE"
    if (
        use["mode"] in ("bag", "choice")
        and league_game in GAMES
        and league_game not in use["games"]
    ):
        return "ITEM_INCOMPATIBLE_WITH_GAME"
    return None


def describe_use(shop_code, league_game=None):
    """The read model's view of one catalog item for one trainer."""
    use = use_of(shop_code)
    refusal = purchase_refusal(shop_code, league_game)
    return {
        "mode": use["mode"],
        "games": list(use["games"]),
        "compatible": None if league_game not in GAMES else refusal is None,
        "reason": refusal,
        "options": [
            {
                "code": code,
                "name": BAG_ITEMS[code][1],
                "item_id": BAG_ITEMS[code][0],
                "games": list(item_games(code)),
            }
            for code in use["items"]
        ],
    }
