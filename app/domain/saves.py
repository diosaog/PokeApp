from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    SaveId,
    TrainerId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_int,
    require_positive_int,
)
from app.domain.pokemon import PrivatePokemon


@dataclass(frozen=True)
class InventoryItem:
    item_id: str
    name: str
    quantity: int
    pocket: str = ""
    category: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "item_id", require_id(self.item_id, "inventory_item.item_id"))
        name = clean_text(self.name)
        if not name:
            raise ValueError("inventory_item.name must be non-empty.")
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "quantity", require_non_negative_int(self.quantity, "inventory_item.quantity"))
        object.__setattr__(self, "pocket", clean_text(self.pocket))
        object.__setattr__(self, "category", clean_text(self.category))


@dataclass(frozen=True)
class PartySlot:
    slot_number: int
    pokemon: PrivatePokemon | None = None

    def __post_init__(self) -> None:
        slot = require_positive_int(self.slot_number, "party_slot.slot_number")
        if slot > 6:
            raise ValueError("party_slot.slot_number must be between 1 and 6.")
        object.__setattr__(self, "slot_number", slot)


@dataclass(frozen=True)
class BoxSlot:
    box_number: int
    slot_number: int
    pokemon: PrivatePokemon | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "box_number", require_positive_int(self.box_number, "box_slot.box_number"))
        slot = require_positive_int(self.slot_number, "box_slot.slot_number")
        if slot > 30:
            raise ValueError("box_slot.slot_number must be between 1 and 30.")
        object.__setattr__(self, "slot_number", slot)


@dataclass(frozen=True)
class PokemonBox:
    box_number: int
    name: str
    slots: tuple[BoxSlot, ...]
    capacity: int = 30

    def __post_init__(self) -> None:
        box = require_positive_int(self.box_number, "pokemon_box.box_number")
        object.__setattr__(self, "box_number", box)
        object.__setattr__(self, "name", clean_text(self.name) or f"Box {box}")
        capacity = require_positive_int(self.capacity, "pokemon_box.capacity")
        object.__setattr__(self, "capacity", capacity)
        slots = tuple(self.slots)
        if len(slots) != capacity:
            raise ValueError("pokemon_box.slots must preserve every slot, including empty slots.")
        for slot in slots:
            if slot.box_number != box:
                raise ValueError("pokemon_box.slots contain a slot from another box.")
        object.__setattr__(self, "slots", slots)


@dataclass(frozen=True)
class SaveRecord:
    id: SaveId
    trainer_id: TrainerId
    filename: str
    original_name: str
    sha256: str
    uploaded_at: UtcTimestamp
    file_ref: str = ""
    is_current: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "save_record.id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "save_record.trainer_id"))
        object.__setattr__(self, "filename", require_id(self.filename, "save_record.filename"))
        object.__setattr__(self, "original_name", clean_text(self.original_name) or self.filename)
        object.__setattr__(self, "sha256", clean_text(self.sha256))
        if not self.sha256:
            raise ValueError("save_record.sha256 must be non-empty.")
        object.__setattr__(self, "uploaded_at", clean_text(self.uploaded_at))
        object.__setattr__(self, "file_ref", optional_id(self.file_ref))


@dataclass(frozen=True)
class ParsedSave:
    schema_version: int
    save_record_id: SaveId
    trainer_id: TrainerId
    party: tuple[PartySlot, ...] = field(default_factory=tuple)
    boxes: tuple[PokemonBox, ...] = field(default_factory=tuple)
    inventory: tuple[InventoryItem, ...] = field(default_factory=tuple)
    badges_count: int = 0
    dead_count: int = 0
    game_code: str = ""
    parsed_at: UtcTimestamp = ""
    source_hash: str = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "schema_version", require_positive_int(self.schema_version, "parsed_save.schema_version"))
        object.__setattr__(self, "save_record_id", require_id(self.save_record_id, "parsed_save.save_record_id"))
        object.__setattr__(self, "trainer_id", require_id(self.trainer_id, "parsed_save.trainer_id"))
        object.__setattr__(self, "party", tuple(sorted(self.party, key=lambda slot: slot.slot_number)))
        object.__setattr__(self, "boxes", tuple(sorted(self.boxes, key=lambda box: box.box_number)))
        object.__setattr__(self, "inventory", tuple(self.inventory))
        object.__setattr__(self, "badges_count", require_non_negative_int(self.badges_count, "parsed_save.badges_count"))
        object.__setattr__(self, "dead_count", require_non_negative_int(self.dead_count, "parsed_save.dead_count"))
        object.__setattr__(self, "game_code", clean_text(self.game_code))
        object.__setattr__(self, "parsed_at", clean_text(self.parsed_at))
        object.__setattr__(self, "source_hash", clean_text(self.source_hash))
