from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    PokemonId,
    clean_text,
    optional_id,
    require_non_negative_int,
)


@dataclass(frozen=True)
class StatSpread:
    hp: int = 0
    atk: int = 0
    defense: int = 0
    spa: int = 0
    spd: int = 0
    spe: int = 0

    def __post_init__(self) -> None:
        for key in ("hp", "atk", "defense", "spa", "spd", "spe"):
            object.__setattr__(
                self,
                key,
                require_non_negative_int(getattr(self, key), f"stat_spread.{key}"),
            )


@dataclass(frozen=True)
class PokemonMove:
    name: str
    move_id: int | None = None
    pp: int | None = None

    def __post_init__(self) -> None:
        name = clean_text(self.name)
        if not name:
            raise ValueError("pokemon_move.name must be non-empty.")
        object.__setattr__(self, "name", name)
        if self.move_id is not None:
            object.__setattr__(
                self,
                "move_id",
                require_non_negative_int(self.move_id, "pokemon_move.move_id"),
            )
        if self.pp is not None:
            object.__setattr__(self, "pp", require_non_negative_int(self.pp, "pokemon_move.pp"))


@dataclass(frozen=True)
class PokemonFlags:
    dead: bool = False
    shielded: bool = False
    stolen: bool = False
    revived: bool = False


@dataclass(frozen=True)
class PublicPokemon:
    """Pokemon data allowed in public contexts such as rival preview or Hall."""

    id: PokemonId = ""
    species: str = ""
    nickname: str = ""
    level: int | None = None
    gender: str = ""
    types: tuple[str, ...] = field(default_factory=tuple)
    item: str = ""
    moves: tuple[PokemonMove, ...] = field(default_factory=tuple)
    sprite_url: str = ""
    form_name: str = ""
    form_index: int | None = None
    is_shiny: bool = False
    flags: PokemonFlags = field(default_factory=PokemonFlags)
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", optional_id(self.id))
        species = clean_text(self.species)
        if not species:
            raise ValueError("public_pokemon.species must be non-empty.")
        object.__setattr__(self, "species", species)
        object.__setattr__(self, "nickname", clean_text(self.nickname))
        if self.level is not None:
            object.__setattr__(self, "level", require_non_negative_int(self.level, "public_pokemon.level"))
        object.__setattr__(self, "gender", clean_text(self.gender))
        object.__setattr__(self, "types", tuple(clean_text(t) for t in self.types if clean_text(t))[:2])
        object.__setattr__(self, "item", clean_text(self.item))
        object.__setattr__(self, "moves", tuple(self.moves)[:4])
        object.__setattr__(self, "sprite_url", clean_text(self.sprite_url))
        object.__setattr__(self, "form_name", clean_text(self.form_name))


@dataclass(frozen=True)
class PrivatePokemon(PublicPokemon):
    """Owner/admin Pokemon data. IVs, EVs, nature and ability are private."""

    ability: str = ""
    nature: str = ""
    ivs: StatSpread | None = None
    evs: StatSpread | None = None
    original_trainer: str = ""

    def __post_init__(self) -> None:
        super().__post_init__()
        object.__setattr__(self, "ability", clean_text(self.ability))
        object.__setattr__(self, "nature", clean_text(self.nature))
        object.__setattr__(self, "original_trainer", clean_text(self.original_trainer))

    def to_public(self) -> PublicPokemon:
        return PublicPokemon(
            id=self.id,
            species=self.species,
            nickname=self.nickname,
            level=self.level,
            gender=self.gender,
            types=self.types,
            item=self.item,
            moves=self.moves,
            sprite_url=self.sprite_url,
            form_name=self.form_name,
            form_index=self.form_index,
            is_shiny=self.is_shiny,
            flags=self.flags,
            metadata=self.metadata,
        )
