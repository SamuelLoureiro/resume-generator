"""Pydantic v2 schemas and loader for verified atomic candidate facts.

Governed by Phase P4 of docs/research_plan.md to serve as the ground truth
for candidate claims, metric extraction, and verb scope ceiling verification.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.config import get_settings

logger = logging.getLogger(__name__)

# Verb Scope Ladder (Scope Levels 1 to 4) per research plan section 5
SCOPE_LEVEL_NAMES: dict[int, str] = {
    1: "participated",  # participated in, assisted, supported, took part in
    2: "contributed",   # contributed to, co-designed, co-developed, helped build
    3: "developed",     # developed, built, implemented, integrated, trained, wrote
    4: "led",           # led, managed, owned, founded, directed, coordinated, spearheaded
}


class AtomicFact(BaseModel):
    """Represents a single atomic, verified claim about the candidate's background.

    Attributes:
        id: Unique identifier for the atomic fact (e.g. 'exp_asimov_leadership').
        source: Reference pointer to the origin bullet in candidate_profile.yaml.
        text: Precise factual claim in plain language.
        scope_ceiling: Strongest allowable verb level (1=participated, 2=contributed, 3=developed, 4=led).
        tracks: Technical tracks for which this fact is relevant (e.g. 'backend', 'ai', 'embedded').
        priority: Importance level (1=critical/core, 2=medium, 3=secondary/supporting).
        metrics: Verifiable quantitative metrics or numbers (e.g. ['5+ developers', '80% accuracy']).
        tags: Relevant technology keywords and thematic tags.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str = Field(..., description="Unique atomic fact identifier")
    source: str = Field(
        default="candidate_profile",
        description="Pointer to profile origin (e.g. experience.asimov_jr.bullet_1)",
    )
    text: str = Field(..., description="Factual claim statement")
    scope_ceiling: int = Field(
        ...,
        ge=1,
        le=4,
        description="Max truthful verb scope (1=participated, 2=contributed, 3=developed, 4=led)",
    )
    tracks: list[str] = Field(
        default_factory=list,
        description="Relevant job tracks (e.g. ai, data, backend, core_swe, embedded)",
    )
    priority: int = Field(
        default=2,
        ge=1,
        le=3,
        description="Relevance priority (1=high/core, 2=medium, 3=low/secondary)",
    )
    metrics: list[str] = Field(
        default_factory=list,
        description="Verifiable quantitative numbers/metrics associated with this fact",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Associated technology keywords, frameworks, or domain tags",
    )

    @property
    def scope_name(self) -> str:
        """Return the English label of the scope ceiling."""
        return SCOPE_LEVEL_NAMES.get(self.scope_ceiling, "unknown")


class CandidateFacts(BaseModel):
    """Collection of all verified atomic facts for a candidate.

    Attributes:
        facts: List of AtomicFact instances.
    """

    model_config = ConfigDict(extra="ignore")

    facts: list[AtomicFact] = Field(
        default_factory=list,
        description="List of verified atomic facts",
    )

    @model_validator(mode="after")
    def validate_unique_fact_ids(self) -> CandidateFacts:
        """Ensure all fact IDs in the collection are strictly unique."""
        seen_ids: set[str] = set()
        duplicates: set[str] = set()
        for fact in self.facts:
            if fact.id in seen_ids:
                duplicates.add(fact.id)
            seen_ids.add(fact.id)
        if duplicates:
            raise ValueError(f"Duplicate atomic fact IDs found: {sorted(duplicates)}")
        return self

    def get_by_id(self, fact_id: str) -> AtomicFact | None:
        """Retrieve a specific fact by its unique ID.

        Args:
            fact_id: Unique fact identifier.

        Returns:
            AtomicFact instance if found, None otherwise.
        """
        for fact in self.facts:
            if fact.id == fact_id:
                return fact
        return None

    def filter_by_track(self, track: str) -> list[AtomicFact]:
        """Filter facts relevant to a given technical track.

        Args:
            track: Track name (e.g. 'ai', 'backend', 'embedded').

        Returns:
            list[AtomicFact]: Facts that include the track or are general.
        """
        normalized_track = track.strip().lower()
        return [
            fact for fact in self.facts
            if normalized_track in [t.lower() for t in fact.tracks] or "general" in [t.lower() for t in fact.tracks]
        ]

    def filter_by_priority(self, max_priority: int = 2) -> list[AtomicFact]:
        """Filter facts with priority <= max_priority (1=high, 2=medium, 3=low).

        Args:
            max_priority: Maximum priority number to include.

        Returns:
            list[AtomicFact]: Filtered list of priority facts.
        """
        return [fact for fact in self.facts if fact.priority <= max_priority]

    def rank_facts_for_job(
        self,
        job: Any,
        track: str | None = None,
    ) -> list[AtomicFact]:
        """Rank and prioritize facts for a target job posting.

        Enables highly relevant priority-2 facts (e.g. Asimov awards) with high keyword
        and track match to outrank less relevant priority-1 facts when space is constrained.
        Specifically, Asimov awards (exp_asimov_member_of_month, exp_asimov_mobile_area_of_month)
        are strongly boosted and preserved for jobs whose track includes embedded or ai.

        Weighting formula:
        - Base priority: (4 - priority) * 2.0 (P1 = 6.0, P2 = 4.0, P3 = 2.0)
        - Track match: +4.0 if primary track matches, +1.0 for general facts
        - Keyword overlap: +1.5 per matched job technology/keyword
        - Special awards boost: +5.0 for award facts when job track includes embedded/ai

        Args:
            job: Target JobPosting instance or object with technologies/keywords.
            track: Explicit track slug (e.g. 'embedded', 'ai', 'backend').

        Returns:
            list[AtomicFact]: Facts sorted by descending composite score.
        """
        job_track = (track or getattr(job, "track", "") or "").lower().strip()
        job_techs = {t.lower().strip() for t in (getattr(job, "technologies", []) or [])}
        job_keywords = {k.lower().strip() for k in (getattr(job, "keywords", []) or [])}
        job_tokens = job_techs | job_keywords
        if hasattr(job, "title"):
            job_tokens.update(str(job.title).lower().split())

        target_is_embedded_or_ai = any(
            t in job_track for t in ("embedded", "ai", "edge")
        ) or any(
            any(w in t for w in ("embed", "ecu", "tinyml", "edge", "ai", "ml"))
            for t in job_tokens
        )

        award_fact_ids = {
            "exp_asimov_awards",
            "exp_asimov_member_of_month",
            "exp_asimov_mobile_area_of_month",
        }

        scored: list[tuple[float, int, AtomicFact]] = []
        for idx, fact in enumerate(self.facts):
            # Base priority score: P1 -> 6.0, P2 -> 4.0, P3 -> 2.0
            score = (4.0 - float(fact.priority)) * 2.0

            # Track match
            fact_tracks = {t.lower().strip() for t in fact.tracks}
            if job_track and job_track in fact_tracks:
                score += 4.0
            elif "general" in fact_tracks:
                score += 1.0

            # Keyword and tag overlap
            fact_tags = {t.lower().strip() for t in fact.tags}
            fact_words = set(fact.text.lower().split())
            overlap = len((fact_tags | fact_words) & job_tokens)
            score += min(overlap * 1.5, 6.0)

            # Special preservation: Asimov awards for jobs with embedded or ai
            if fact.id in award_fact_ids and target_is_embedded_or_ai:
                score += 5.0

            scored.append((score, idx, fact))

        scored.sort(key=lambda x: (-x[0], x[1]))
        return [f for _, _, f in scored]

    def get_allowed_metrics(self) -> set[str]:
        """Extract a set of all verifiable quantitative metric strings across facts."""
        metrics_set: set[str] = set()
        for fact in self.facts:
            for metric in fact.metrics:
                if metric.strip():
                    metrics_set.add(metric.strip())
        return metrics_set

    def get_allowed_tags(self) -> set[str]:
        """Extract a set of all normalized technology tags and skills."""
        tags_set: set[str] = set()
        for fact in self.facts:
            for tag in fact.tags:
                if tag.strip():
                    tags_set.add(tag.strip().lower())
        return tags_set

    def __len__(self) -> int:
        """Return the number of facts in the collection."""
        return len(self.facts)


def load_candidate_facts(facts_path: Path | str | None = None) -> CandidateFacts:
    """Load and validate verified candidate atomic facts from a YAML file.

    Args:
        facts_path: Path to candidate facts YAML. If None, uses settings.candidate_facts_path.

    Returns:
        CandidateFacts: Validated collection of atomic facts.

    Raises:
        FileNotFoundError: If the specified facts YAML file does not exist.
        ValueError: If YAML content cannot be parsed or fails schema validation.
    """
    if facts_path is None:
        settings = get_settings()
        target_path = Path(settings.candidate_facts_path)
    else:
        target_path = Path(facts_path)

    if not target_path.exists():
        raise FileNotFoundError(f"Candidate facts file not found at: {target_path}")

    try:
        raw_text = target_path.read_text(encoding="utf-8")
        parsed = yaml.safe_load(raw_text)
    except Exception as exc:
        logger.error("Failed to read YAML from %s: %s", target_path, exc)
        raise ValueError(f"Malformed YAML in candidate facts file: {exc}") from exc

    if parsed is None:
        return CandidateFacts(facts=[])

    if isinstance(parsed, list):
        parsed = {"facts": parsed}
    elif not isinstance(parsed, dict):
        raise ValueError(
            f"Expected YAML dictionary or list in candidate facts, got {type(parsed).__name__}"
        )

    try:
        facts_collection = CandidateFacts.model_validate(parsed)
        logger.info(
            "Loaded %d verified atomic facts from %s",
            len(facts_collection),
            target_path,
        )
        return facts_collection
    except Exception as exc:
        logger.error("Schema validation failed for candidate facts from %s: %s", target_path, exc)
        raise ValueError(f"Invalid candidate facts schema: {exc}") from exc
