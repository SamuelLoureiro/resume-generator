"""Bullet-to-fact matching shared by M2 (inflation) and M3 (coverage).

Matching is deterministic: Dice similarity over content tokens, restricted to the
facts that belong to the same resume entry (experience / project) whenever that
entry can be recognised from the fact ``source`` pointer.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from src.data.facts import AtomicFact, CandidateFacts
from src.data.resume import TailoredResume
from src.verification.text_utils import similarity

DEFAULT_MATCH_THRESHOLD: float = 0.30
"""Minimum Dice similarity for a bullet to count as an expression of a fact.

Chosen by inspecting score gaps on the Amazon golden fixtures and on a resume built
verbatim from the profile: bullets that really express a fact score >= 0.31 (one
borderline case, the first SPE bullet), fabricated-looking bullets score <= 0.29. This is
a heuristic fitted to two fixtures, not a validated value, and results near the
threshold are fragile; unmatched bullets are never silently accepted (they are handed to
the claim-level judge in phase P6).
"""

_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def _alnum(text: str) -> str:
    return _ALNUM_RE.sub("", (text or "").lower())


@dataclass(frozen=True)
class BulletRef:
    """A resume bullet together with the entry it belongs to.

    Attributes:
        text: Bullet text.
        kind: ``"experience"`` or ``"project"``.
        entry: Organization + title (experience) or project name (project).
    """

    text: str
    kind: str
    entry: str


class BulletMatch(BaseModel):
    """Result of matching one bullet against the atomic facts.

    Attributes:
        bullet: Bullet text.
        kind: Section kind of the bullet.
        entry: Entry the bullet belongs to.
        fact_id: Best-matching fact id, or None if below threshold.
        score: Similarity of the best candidate (even when below threshold).
        best_fact_id: Best candidate regardless of threshold (diagnostics).
    """

    model_config = ConfigDict(frozen=True)

    bullet: str
    kind: str
    entry: str
    fact_id: str | None = None
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    best_fact_id: str | None = None


def extract_bullets(resume: TailoredResume) -> list[BulletRef]:
    """List every experience and project bullet of a resume.

    Args:
        resume: Structured resume.

    Returns:
        list[BulletRef]: Bullets in document order.
    """
    refs: list[BulletRef] = []
    for exp in resume.experiences:
        entry = f"{exp.organization} {exp.title}"
        refs.extend(BulletRef(b, "experience", entry) for b in exp.bullets if b.strip())
    for proj in resume.projects:
        refs.extend(BulletRef(b, "project", proj.name) for b in proj.bullets if b.strip())
    return refs


def _source_kind_and_entity(source: str) -> tuple[str, list[str]]:
    """Split ``experience.asimov_jr.bullet_1`` into ``("experience", ["asimov", "jr"])``."""
    parts = source.split(".")
    kind = parts[0] if parts else ""
    entity_parts = parts[1].split("_") if len(parts) > 1 else []
    return kind, [p for p in entity_parts if p]


def _fact_belongs_to_entry(fact: AtomicFact, ref: BulletRef) -> bool:
    kind, entity = _source_kind_and_entity(fact.source)
    if kind != ref.kind or not entity:
        return False
    haystack = _alnum(ref.entry)
    return all(part in haystack for part in entity)


def candidate_facts_for(ref: BulletRef, facts: CandidateFacts) -> list[AtomicFact]:
    """Return the facts a bullet may be an expression of.

    Facts of the same recognised entry are preferred; if the entry matches no fact
    entity, every fact is a candidate.

    Args:
        ref: Bullet reference.
        facts: Verified facts.

    Returns:
        list[AtomicFact]: Candidate facts (possibly all facts).
    """
    same_entry = [f for f in facts.facts if _fact_belongs_to_entry(f, ref)]
    return same_entry or list(facts.facts)


def match_bullet(
    ref: BulletRef,
    facts: CandidateFacts,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> BulletMatch:
    """Match one bullet to its nearest fact.

    Args:
        ref: Bullet reference.
        facts: Verified facts.
        threshold: Minimum similarity to accept a match.

    Returns:
        BulletMatch: Match; ``fact_id`` is None when nothing reaches the threshold.
    """
    best: AtomicFact | None = None
    best_score = 0.0
    for fact in candidate_facts_for(ref, facts):
        score = similarity(ref.text, fact.text)
        if score > best_score:
            best, best_score = fact, score
    matched = best.id if best is not None and best_score >= threshold else None
    return BulletMatch(
        bullet=ref.text,
        kind=ref.kind,
        entry=ref.entry,
        fact_id=matched,
        score=round(best_score, 4),
        best_fact_id=best.id if best is not None else None,
    )


def match_resume_bullets(
    resume: TailoredResume,
    facts: CandidateFacts,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> list[BulletMatch]:
    """Match all experience/project bullets of a resume against the facts."""
    return [match_bullet(ref, facts, threshold) for ref in extract_bullets(resume)]
