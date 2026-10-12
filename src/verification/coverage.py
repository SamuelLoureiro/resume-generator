"""M3 — Coverage of the facts that matter for the target job track."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.data.facts import AtomicFact, CandidateFacts
from src.data.resume import TailoredResume
from src.verification.matching import (
    DEFAULT_MATCH_THRESHOLD,
    BulletRef,
    candidate_facts_for,
    extract_bullets,
)
from src.verification.text_utils import similarity


class CoverageResult(BaseModel):
    """Outcome of the M3 check.

    Attributes:
        track: Job track the relevance filter used.
        relevant: Ids of relevant facts (track listed in ``tracks`` and priority <= max).
        covered: Ids of relevant facts expressed by at least one bullet.
        omissions: Ids of relevant priority-1 facts that are missing (critical omissions).
    """

    model_config = ConfigDict(frozen=True)

    track: str
    relevant: list[str] = Field(default_factory=list)
    covered: list[str] = Field(default_factory=list)
    omissions: list[str] = Field(default_factory=list)

    @property
    def coverage(self) -> float | None:
        """Covered ÷ relevant facts; None when no fact is relevant to the track."""
        if not self.relevant:
            return None
        return len(self.covered) / len(self.relevant)


def relevant_facts(facts: CandidateFacts, track: str, max_priority: int = 2) -> list[AtomicFact]:
    """Return facts whose ``tracks`` list the job track and whose priority <= ``max_priority``.

    Unlike :meth:`CandidateFacts.filter_by_track`, facts tagged only ``general`` are not
    included: the research plan defines relevance as "``tracks`` containing the job track".

    Args:
        facts: Verified facts.
        track: Job track assigned by the human (e.g. ``"ai"``, ``"embedded"``).
        max_priority: Highest priority number still counted as relevant.

    Returns:
        list[AtomicFact]: Relevant facts.
    """
    wanted = track.strip().lower()
    return [
        f for f in facts.facts
        if f.priority <= max_priority and wanted in {t.lower() for t in f.tracks}
    ]


def _expresses(ref: BulletRef, fact: AtomicFact, threshold: float) -> bool:
    return similarity(ref.text, fact.text) >= threshold


def check_coverage(
    resume: TailoredResume,
    facts: CandidateFacts,
    track: str,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    max_priority: int = 2,
) -> CoverageResult:
    """Measure how many track-relevant facts the resume expresses.

    A fact counts as covered if any bullet of the same entry (or any bullet, when the
    entry is not recognised) reaches the similarity threshold against it. One bullet
    may cover several facts.

    Args:
        resume: Structured resume.
        facts: Verified facts.
        track: Job track.
        threshold: Similarity threshold (same as bullet-to-fact matching).
        max_priority: Highest priority counted as relevant.

    Returns:
        CoverageResult: Relevant, covered and critically omitted fact ids.
    """
    relevant = relevant_facts(facts, track, max_priority)
    bullets = extract_bullets(resume)
    covered: list[str] = []
    for fact in relevant:
        for ref in bullets:
            if fact in candidate_facts_for(ref, facts) and _expresses(ref, fact, threshold):
                covered.append(fact.id)
                break
    covered_set = set(covered)
    omissions = [f.id for f in relevant if f.priority == 1 and f.id not in covered_set]
    return CoverageResult(
        track=track,
        relevant=[f.id for f in relevant],
        covered=covered,
        omissions=omissions,
    )
