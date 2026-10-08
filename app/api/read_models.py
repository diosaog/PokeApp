"""Browser read projections. No raw metadata, storage paths or identity evidence."""

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field
from app.api.cup_models import CupSide
from app.api.progress_models import ProgressRead


class SeasonRead(BaseModel):
    id: UUID
    name: str
    status: str
    current_matchday_id: UUID | None = None
    initial_assignment_rule: Literal["observed_deaths_v1"] | None = None


class SeasonPage(BaseModel):
    items: list[SeasonRead]
    next_offset: int | None


class TrainerRead(BaseModel):
    id: UUID
    display_name: str


class PlayerRead(BaseModel):
    id: UUID
    trainer_id: UUID
    status: str
    display_name: str
    badges_count: int | None = None
    progress: ProgressRead = Field(default_factory=ProgressRead)


class DayRead(BaseModel):
    id: UUID
    number: int
    status: str


class MatchRead(BaseModel):
    id: UUID
    matchday_id: UUID
    division_id: UUID
    player_a_id: UUID
    player_b_id: UUID
    winner_id: UUID | None
    status: str


class MoveRead(BaseModel):
    name: str
    pp: int | None = None


class PokemonRead(BaseModel):
    species: str
    nickname: str = ""
    level: int | None = None
    types: list[str] = Field(default_factory=list)
    item: str = ""
    moves: list[MoveRead] = Field(default_factory=list)
    is_shiny: bool = False


class StatsRead(BaseModel):
    hp: int
    atk: int
    defense: int
    spa: int
    spd: int
    spe: int


class PrivatePokemonRead(PokemonRead):
    ability: str = ""
    nature: str = ""
    ivs: StatsRead | None = None
    evs: StatsRead | None = None


class LockRead(BaseModel):
    trainer_id: UUID
    matchday_id: UUID
    locked_at: datetime
    is_late: bool
    public_team_snapshot: list[PokemonRead]


class DivisionRead(BaseModel):
    id: UUID
    code: str
    name: str


class MembershipRead(BaseModel):
    season_player_id: UUID
    division_id: UUID
    effective_from_matchday_number: int
    effective_to_matchday_number: int | None
    eligibility_ends_before_matchday_number: int | None


class StandingRead(BaseModel):
    # V2 snapshot 'trainer_id' is a season-player ID, never a trainer ID.
    season_player_id: UUID
    division: str
    position: int
    division_position: int
    points_awarded: int
    score: Decimal
    position_end: int | None = Field(default=None, ge=1)
    tie_status: Literal["unique", "externally_resolved", "unresolved_neutral"] | None = None


class SnapshotRead(BaseModel):
    matchday_id: UUID
    revision: int
    closed_at: datetime
    standings: list[StandingRead]


class PointsRead(BaseModel):
    season_player_id: UUID
    earned_points: Decimal
    points_reduction: Decimal
    dead_points_penalty: Decimal
    sanctioned_points: Decimal
    source_matchday_id: UUID


class OverviewRead(BaseModel):
    season: SeasonRead
    players: list[PlayerRead]
    days: list[DayRead]
    matches: list[MatchRead]
    divisions: list[DivisionRead]
    memberships: list[MembershipRead]
    snapshots: list[SnapshotRead]
    points: list[PointsRead]
    locks: list[LockRead]
    balance: str | None = Field(pattern=r"^-?(0|[1-9][0-9]*)$")


class LeagueStandingRead(BaseModel):
    season_player_id: UUID
    trainer_id: UUID
    display_name: str
    status: str
    total_points: Decimal = Field(allow_inf_nan=False)
    points_source_matchday_id: UUID | None
    coin_balance: str = Field(pattern=r"^-?(0|[1-9][0-9]*)$")
    dead_count: int | None = Field(ge=0, le=30)
    dead_count_source: Literal["observed_current_save", "unknown"]
    dead_count_observed_at: datetime | None


class LeagueGeneralRead(BaseModel):
    season: SeasonRead
    days: list[DayRead]
    # Server ordering is presentation only; no sporting rank or inferred title.
    rows: list[LeagueStandingRead] = Field(max_length=500)


class SaveRead(BaseModel):
    id: UUID
    parser_status: str
    parser_version: str
    uploaded_at: datetime


class SlotRead(BaseModel):
    location: str
    pokemon_entity_id: UUID | None = None
    pokemon: PrivatePokemonRead


class PCRead(BaseModel):
    save: SaveRead | None
    status: Literal["no_current_save", "not_ready", "ready", "unsupported_payload"]
    pokemon: list[SlotRead]


class ItemRead(BaseModel):
    id: UUID
    code: str
    name: str
    category: str
    description: str
    base_price: int


class PromotionRead(BaseModel):
    id: UUID
    shop_item_id: UUID
    status: str
    effective_price: int
    stock_total: int | None
    stock_used: int
    activates_at: datetime | None = None
    ends_at: datetime | None = None


class ShopRead(BaseModel):
    items: list[ItemRead]
    promotions: list[PromotionRead]
    balance: str | None = Field(pattern=r"^-?(0|[1-9][0-9]*)$")
    season_status: str


class PurchaseRead(BaseModel):
    id: UUID
    shop_item_id: UUID
    status: str
    total_price: int
    purchased_at: datetime
    item_name: str
    item_code: str
    acquisition_type: Literal["paid", "reward"] = "paid"


class TargetRead(BaseModel):
    pokemon_entity_id: UUID
    trainer_id: UUID
    location: str
    visibility: Literal["own", "public_team_lock"]
    can_shield: bool = False
    pokemon: PokemonRead


class InventoryRead(BaseModel):
    purchases: list[PurchaseRead]
    targets: list[TargetRead]


class HallRead(BaseModel):
    id: UUID
    season_id: UUID
    competition_type: str
    champion_trainer_id: UUID | None
    finalist_trainer_id: UUID | None
    finalized_at: datetime
    cup_id: UUID | None
    cup_certificate_id: UUID | None
    champion_side_id: UUID | None
    finalist_side_id: UUID | None
    cup_sides: list[CupSide] | None
    cup_checksum: str | None


class HallPage(BaseModel):
    items: list[HallRead]
    next_offset: int | None
