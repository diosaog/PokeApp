from __future__ import annotations

# Traducciones y helpers de presentación (ES)

# Abreviaturas de stats (se usan en Naturalezas)
STAT_ABBR: dict[str, str] = {
    "attack": "Atk",
    "special-attack": "SpA",
    "defense": "Def",
    "special-defense": "SpD",
    "speed": "Spe",
}

# Naturalezas en español: nombre y stats que suben/bajan
NATURES_ES: dict[str, tuple[str, str | None, str | None]] = {
    "Hardy":   ("Fuerte",  None, None),
    "Lonely":  ("Huraña",  "attack", "defense"),
    "Brave":   ("Audaz",   "attack", "speed"),
    "Adamant": ("Firme",   "attack", "special-attack"),
    "Naughty": ("Pícara",  "attack", "special-defense"),

    "Bold":    ("Osada",   "defense", "attack"),
    "Docile":  ("Dócil",   None, None),
    "Relaxed": ("Plácida", "defense", "speed"),
    "Impish":  ("Agitada", "defense", "special-attack"),
    "Lax":     ("Floja",   "defense", "special-defense"),

    "Timid":   ("Miedosa", "speed", "attack"),
    "Hasty":   ("Activa",  "speed", "defense"),
    "Serious": ("Seria",   None, None),
    "Jolly":   ("Alegre",  "speed", "special-attack"),
    "Naive":   ("Ingenua", "speed", "special-defense"),

    "Modest":  ("Modesta", "special-attack", "attack"),
    "Mild":    ("Afable",  "special-attack", "defense"),
    "Quiet":   ("Mansa",   "special-attack", "speed"),
    "Bashful": ("Tímida",  None, None),
    "Rash":    ("Alocada", "special-attack", "special-defense"),

    "Calm":    ("Serena",  "special-defense", "attack"),
    "Gentle":  ("Amable",  "special-defense", "defense"),
    "Sassy":   ("Grosera", "special-defense", "speed"),
    "Careful": ("Cauta",   "special-defense", "special-attack"),
    "Quirky":  ("Rara",    None, None),
}


def nature_display_es(nature_val: str | None) -> str:
    if not nature_val:
        return "-"
    key = str(nature_val).strip()
    key_norm = key.lower().capitalize()
    data = NATURES_ES.get(key) or NATURES_ES.get(key_norm)
    if not data:
        return key
    name_es, up, down = data
    if up and down:
        return f"{name_es} (+{STAT_ABBR[up]}-{STAT_ABBR[down]})"
    return name_es


# Tipos (EN -> ES)
TYPE_ES: dict[str, str] = {
    "Normal": "Normal",
    "Fire": "Fuego",
    "Water": "Agua",
    "Electric": "Eléctrico",
    "Grass": "Planta",
    "Ice": "Hielo",
    "Fighting": "Lucha",
    "Poison": "Veneno",
    "Ground": "Tierra",
    "Flying": "Volador",
    "Psychic": "Psíquico",
    "Bug": "Bicho",
    "Rock": "Roca",
    "Ghost": "Fantasma",
    "Dragon": "Dragón",
    "Dark": "Siniestro",
    "Steel": "Acero",
    "Fairy": "Hada",
}


def translate_type_es(t: str | None) -> str:
    if not t:
        return "-"
    return TYPE_ES.get(str(t).title(), str(t))


def translate_types_es(types: list[str] | None) -> list[str]:
    if not types:
        return []
    return [translate_type_es(t) for t in types]


# Nota: este archivo contiene las etiquetas ya corregidas con tildes/ñ.

