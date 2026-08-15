from __future__ import annotations

from app.domain.trials import TrialStatus, TrialVerdict, TrialVote


def jury_vote_counts(votes: list[str] | tuple[str, ...]) -> tuple[int, int]:
    guilty = sum(1 for vote in votes if str(vote) == TrialVote.GUILTY.value)
    not_guilty = sum(1 for vote in votes if str(vote) == TrialVote.NOT_GUILTY.value)
    return guilty, not_guilty


def jury_majority(jury_size: int) -> int:
    return int(jury_size) // 2 + 1


def verdict_from_votes(votes: list[str] | tuple[str, ...], *, jury_size: int) -> TrialVerdict:
    guilty, not_guilty = jury_vote_counts(votes)
    majority = jury_majority(jury_size)
    if guilty >= majority:
        return TrialVerdict.GUILTY
    if not_guilty >= majority:
        return TrialVerdict.NOT_GUILTY
    return TrialVerdict.PENDING


def status_transition_allowed(current: str, target: str) -> bool:
    current_status = str(current or TrialStatus.PROPOSED.value)
    target_status = str(target or TrialStatus.PROPOSED.value)
    if current_status == target_status:
        return True
    allowed = {
        TrialStatus.PROPOSED.value: {TrialStatus.IN_PROGRESS.value},
        TrialStatus.IN_PROGRESS.value: {TrialStatus.FINISHED.value},
        TrialStatus.FINISHED.value: set(),
    }
    return target_status in allowed.get(current_status, set())
