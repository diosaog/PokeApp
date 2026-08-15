from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.common import (
    JsonObject,
    SeasonId,
    TrainerId,
    TrialId,
    UtcTimestamp,
    clean_text,
    optional_id,
    require_id,
    require_non_negative_float,
    require_non_negative_int,
    require_positive_int,
    StringEnum,
)


class TrialStatus(StringEnum):
    PROPOSED = "proposed"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class TrialVerdict(StringEnum):
    PENDING = "pending"
    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"


class TrialVote(StringEnum):
    GUILTY = "guilty"
    NOT_GUILTY = "not_guilty"


class PenaltyType(StringEnum):
    STORE_BAN = "store_ban"
    COINS_REDUCTION = "coins_reduction"
    POKEMON_RELEASE = "pokemon_release"
    POINTS_REDUCTION = "points_reduction"
    OTHER = "other"


@dataclass(frozen=True)
class Penalty:
    type: PenaltyType
    amount: float = 0.0
    text: str = ""
    start_matchday: int | None = None
    end_matchday: int | None = None
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "amount", require_non_negative_float(self.amount, "penalty.amount"))
        object.__setattr__(self, "text", clean_text(self.text))
        if self.start_matchday is not None:
            object.__setattr__(self, "start_matchday", require_positive_int(self.start_matchday, "penalty.start_matchday"))
        if self.end_matchday is not None:
            object.__setattr__(self, "end_matchday", require_positive_int(self.end_matchday, "penalty.end_matchday"))


@dataclass(frozen=True)
class JuryVote:
    jury_trainer_id: TrainerId
    vote: TrialVote
    voted_at: UtcTimestamp = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "jury_trainer_id", require_id(self.jury_trainer_id, "jury_vote.jury_trainer_id"))
        object.__setattr__(self, "voted_at", clean_text(self.voted_at))


@dataclass(frozen=True)
class TrialCase:
    id: TrialId
    season_id: SeasonId
    case_no: int
    title: str
    creator_id: TrainerId
    accused_id: TrainerId
    status: TrialStatus = TrialStatus.PROPOSED
    verdict: TrialVerdict = TrialVerdict.PENDING
    summary: str = ""
    hearing_date: str = ""
    is_public: bool = True
    evidence: str = ""
    witnesses: str = ""
    priority: str = "medium"
    category: str = ""
    public_vote: bool = False
    jury_size: int = 5
    jury_votes: tuple[JuryVote, ...] = field(default_factory=tuple)
    resolution_notes: str = ""
    penalties: tuple[Penalty, ...] = field(default_factory=tuple)
    created_at: UtcTimestamp = ""
    updated_at: UtcTimestamp = ""
    resolved_at: UtcTimestamp = ""
    metadata: JsonObject = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", require_id(self.id, "trial_case.id"))
        object.__setattr__(self, "season_id", require_id(self.season_id, "trial_case.season_id"))
        object.__setattr__(self, "case_no", require_positive_int(self.case_no, "trial_case.case_no"))
        object.__setattr__(self, "title", require_id(self.title, "trial_case.title"))
        object.__setattr__(self, "creator_id", require_id(self.creator_id, "trial_case.creator_id"))
        object.__setattr__(self, "accused_id", require_id(self.accused_id, "trial_case.accused_id"))
        object.__setattr__(self, "summary", clean_text(self.summary))
        object.__setattr__(self, "hearing_date", clean_text(self.hearing_date))
        object.__setattr__(self, "evidence", clean_text(self.evidence))
        object.__setattr__(self, "witnesses", clean_text(self.witnesses))
        object.__setattr__(self, "priority", clean_text(self.priority) or "medium")
        object.__setattr__(self, "category", clean_text(self.category))
        object.__setattr__(self, "jury_size", require_positive_int(self.jury_size, "trial_case.jury_size"))
        object.__setattr__(self, "jury_votes", tuple(self.jury_votes))
        object.__setattr__(self, "resolution_notes", clean_text(self.resolution_notes))
        object.__setattr__(self, "penalties", tuple(self.penalties))
        object.__setattr__(self, "created_at", clean_text(self.created_at))
        object.__setattr__(self, "updated_at", clean_text(self.updated_at))
        object.__setattr__(self, "resolved_at", clean_text(self.resolved_at))
