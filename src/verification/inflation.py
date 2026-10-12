"""M2 — Inflation rate: bullets whose lead verb outranks the source fact's scope ceiling."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.data.facts import CandidateFacts
from src.data.resume import TailoredResume
from src.verification.matching import (
    DEFAULT_MATCH_THRESHOLD,
    BulletMatch,
    match_resume_bullets,
)
from src.verification.verb_ladder import (
    design_evidence_in,
    extract_lead_verb,
    verb_words,
)


class InflatedBullet(BaseModel):
    """A bullet judged to overstate the candidate's scope.

    Attributes:
        bullet: Bullet text.
        verb: Lead verb phrase found on the ladder.
        verb_level: Level of that verb (1-4).
        fact_id: Matched fact.
        scope_ceiling: Ceiling of the matched fact.
        reason: Human-readable explanation.
    """

    model_config = ConfigDict(frozen=True)

    bullet: str
    verb: str
    verb_level: int
    fact_id: str
    scope_ceiling: int
    reason: str


class InflationResult(BaseModel):
    """Outcome of the M2 check.

    Attributes:
        inflated: Bullets that overstate scope.
        assessed: Bullets matched to a fact whose lead verb is on the ladder.
        unmatched: Bullets with no fact above the similarity threshold. They cannot be
            scope-checked and are handed to the claim-level judge (M1d, phase P6).
        unranked: Matched bullets whose lead verb is not on the ladder (not assessable).
    """

    model_config = ConfigDict(frozen=True)

    inflated: list[InflatedBullet] = Field(default_factory=list)
    assessed: int = 0
    unmatched: list[BulletMatch] = Field(default_factory=list)
    unranked: list[BulletMatch] = Field(default_factory=list)

    @property
    def rate(self) -> float | None:
        """Inflated ÷ assessed bullets; None when no bullet could be assessed."""
        if self.assessed == 0:
            return None
        return len(self.inflated) / self.assessed


def check_inflation(
    resume: TailoredResume,
    facts: CandidateFacts,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
    matches: list[BulletMatch] | None = None,
) -> InflationResult:
    """Compare each bullet's lead verb with the scope ceiling of its nearest fact.

    A lead verb is accepted without comparison when the exact same word appears in the
    matched fact's own text: the fact is verified, so the verb is grounded verbatim
    (e.g. a fact stating "Managed and developed..." allows the lead verb "Managed").
    Design-type verbs (designed, architected, engineered) additionally need design
    evidence in the matched fact.

    Args:
        resume: Structured resume.
        facts: Verified atomic facts.
        threshold: Similarity threshold for bullet-to-fact matching.
        matches: Optional precomputed matches (avoids recomputation).

    Returns:
        InflationResult: Inflated bullets plus bookkeeping for unassessable bullets.
    """
    matches = matches if matches is not None else match_resume_bullets(resume, facts, threshold)
    inflated: list[InflatedBullet] = []
    unmatched: list[BulletMatch] = []
    unranked: list[BulletMatch] = []
    assessed = 0

    for match in matches:
        if match.fact_id is None:
            unmatched.append(match)
            continue
        fact = facts.get_by_id(match.fact_id)
        lead = extract_lead_verb(match.bullet)
        if fact is None or lead is None:
            unranked.append(match)
            continue
        assessed += 1

        if lead.phrase.split()[0] in verb_words(fact.text):
            continue  # verb copied from the verified fact

        if lead.level > fact.scope_ceiling:
            inflated.append(
                InflatedBullet(
                    bullet=match.bullet,
                    verb=lead.phrase,
                    verb_level=lead.level,
                    fact_id=fact.id,
                    scope_ceiling=fact.scope_ceiling,
                    reason=(
                        f"lead verb '{lead.phrase}' is level {lead.level} but fact "
                        f"'{fact.id}' allows at most level {fact.scope_ceiling} "
                        f"({fact.scope_name})"
                    ),
                )
            )
        elif lead.is_design and not design_evidence_in(fact.text):
            inflated.append(
                InflatedBullet(
                    bullet=match.bullet,
                    verb=lead.phrase,
                    verb_level=lead.level,
                    fact_id=fact.id,
                    scope_ceiling=fact.scope_ceiling,
                    reason=(
                        f"design-type verb '{lead.phrase}' but fact '{fact.id}' does not "
                        "describe design/architecture/engineering work"
                    ),
                )
            )

    return InflationResult(
        inflated=inflated,
        assessed=assessed,
        unmatched=unmatched,
        unranked=unranked,
    )
