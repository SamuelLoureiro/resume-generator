"""M4 — Truthful keyword alignment between a job posting and a resume."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.verification.ground_truth import GroundTruth
from src.verification.text_utils import ngram_keys, split_terms, term_key


class KeywordResult(BaseModel):
    """Outcome of the M4 check.

    Attributes:
        supportable: Job keywords the candidate verifiably has.
        present: Supportable keywords found in the resume.
        missing: Supportable keywords absent from the resume (ATS opportunities lost).
        fabricated: Job keywords the candidate does *not* have but the resume contains.
    """

    model_config = ConfigDict(frozen=True)

    supportable: list[str] = Field(default_factory=list)
    present: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    fabricated: list[str] = Field(default_factory=list)

    @property
    def alignment(self) -> float | None:
        """(job keywords ∩ resume ∩ profile) ÷ (job keywords ∩ profile); None if empty."""
        if not self.supportable:
            return None
        return len(self.present) / len(self.supportable)


def resume_text(resume: TailoredResume) -> str:
    """Concatenate all candidate-claim text of a resume (no header, no target job)."""
    parts: list[str] = []
    if resume.objective_or_summary:
        parts.append(resume.objective_or_summary)
    for edu in resume.education:
        parts.append(edu.degree)
        parts.extend(edu.highlights)
    for exp in resume.experiences:
        parts.extend(exp.bullets)
        parts.extend(exp.technologies)
    for proj in resume.projects:
        parts.extend(proj.bullets)
        parts.extend(proj.technologies)
    for cat in resume.skills:
        parts.extend(cat.skills)
    return "\n".join(parts)


def job_keywords(job: JobPosting) -> list[str]:
    """Return the deduplicated atomic keywords of a job (``technologies`` + ``keywords``)."""
    seen: set[str] = set()
    ordered: list[str] = []
    for raw in [*job.technologies, *job.keywords]:
        for term in split_terms(raw):
            key = term_key(term)
            if key and key not in seen:
                seen.add(key)
                ordered.append(term)
    return ordered


def check_keywords(
    resume: TailoredResume,
    job: JobPosting,
    truth: GroundTruth,
) -> KeywordResult:
    """Compute truthful keyword alignment.

    Keywords the candidate does not have are excluded from the denominator (so the
    metric cannot be raised by claiming them) and reported in ``fabricated`` if the
    resume nevertheless contains them.

    Args:
        resume: Structured resume.
        job: Target job posting.
        truth: Ground-truth lookups.

    Returns:
        KeywordResult: Alignment lists.
    """
    text_keys = ngram_keys(resume_text(resume), max_n=4)
    supportable: list[str] = []
    present: list[str] = []
    missing: list[str] = []
    fabricated: list[str] = []
    for term in job_keywords(job):
        in_resume = term_key(term) in text_keys
        if truth.has_term(term):
            supportable.append(term)
            (present if in_resume else missing).append(term)
        elif in_resume:
            fabricated.append(term)
    return KeywordResult(
        supportable=supportable, present=present, missing=missing, fabricated=fabricated
    )
