"""Single entry point that runs M1–M5 on one resume."""

from __future__ import annotations

from pathlib import Path

from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.verification.coverage import CoverageResult, check_coverage
from src.verification.defect_checks import (
    check_fact_fusion,
    check_job_phrase_echo,
    check_summary_lint,
    check_summary_verbs,
)
from src.verification.fabrication import FabricationResult, check_fabrication
from src.verification.format_checks import FormatResult, check_format
from src.verification.ground_truth import GroundTruth, extract_numbers
from src.verification.inflation import InflationResult, check_inflation
from src.verification.keywords import KeywordResult, check_keywords
from src.verification.matching import DEFAULT_MATCH_THRESHOLD, match_resume_bullets


class VerificationReport(BaseModel):
    """All deterministic metrics for one resume.

    Metrics are reported separately; no aggregate score is computed (research plan,
    section 5). ``coverage`` and ``keywords`` are None when no job/track was supplied.

    Attributes:
        fabrication: M1a–c result.
        inflation: M2 result.
        coverage: M3 result (needs a track).
        keywords: M4 result (needs a job posting).
        format: M5 result.
    """

    model_config = ConfigDict(frozen=True)

    fabrication: FabricationResult
    inflation: InflationResult
    coverage: CoverageResult | None = None
    keywords: KeywordResult | None = None
    format: FormatResult
    defects: list[dict[str, Any]] = Field(default_factory=list)

    @property
    def hard_pass(self) -> bool:
        """Headline metric: no fabrication, no inflation, no failed format check.

        Fabricated job keywords (M4) count as fabrication. Checks that could not run
        (``not_verified``) do not fail the resume but are listed in
        :attr:`not_verified` and must be mentioned when reporting.
        """
        no_fabricated_keywords = self.keywords is None or not self.keywords.fabricated
        return (
            not self.fabrication.unsupported
            and not self.inflation.inflated
            and no_fabricated_keywords
            and self.format.all_passed
        )

    @property
    def defect_free(self) -> bool:
        """True if no Phase B defects (summary lint, job echo, fact fusion, summary verbs) were detected."""
        return len(self.defects) == 0

    @property
    def not_verified(self) -> list[str]:
        """Names of checks/metrics that could not be computed for lack of input."""
        missing = [c.name for c in self.format.not_verified]
        if self.coverage is None:
            missing.append("coverage (no track supplied)")
        if self.keywords is None:
            missing.append("keywords (no job supplied)")
        return missing


def verify_resume(
    resume: TailoredResume,
    profile: CandidateProfile,
    facts: CandidateFacts,
    *,
    job: JobPosting | None = None,
    track: str | None = None,
    tex: str | None = None,
    pdf_path: Path | str | None = None,
    match_threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> VerificationReport:
    """Run the deterministic metrics M1a–c, M2, M3, M4 and M5.

    Offline and deterministic: no LLM or network call is made.

    Args:
        resume: Resume to verify.
        profile: Candidate profile (source of truth for entities, dates, skills).
        facts: Verified atomic facts (source of truth for scope, metrics, coverage).
        job: Target job; enables M4 and lets the summary repeat digits of the job title.
        track: Job track assigned by the human; enables M3.
        tex: Rendered LaTeX, enables the section-title and raw-URL checks.
        pdf_path: Compiled PDF, enables the one-page check.
        match_threshold: Bullet-to-fact similarity threshold.

    Returns:
        VerificationReport: Per-metric results.
    """
    truth = GroundTruth(profile, facts)
    title = job.title if job is not None else resume.target_job_title
    extra_numbers = set(extract_numbers(title or ""))
    for token in list(extra_numbers):
        extra_numbers.add(token.rstrip("+%"))

    matches = match_resume_bullets(resume, facts, match_threshold)
    defects: list[dict[str, Any]] = []
    # B1: Summary lint (forbidden meta-words)
    defects.extend(check_summary_lint(resume, profile))
    # B2: Job phrase echo (n-gram echoing)
    if job is not None:
        defects.extend(check_job_phrase_echo(resume, job, profile, facts))
    # B3: Fact fusion (sentence combining multi-facts)
    defects.extend(check_fact_fusion(resume, facts))
    # B5: Summary verbs (verb ladder across all candidate verbs in summary)
    defects.extend(check_summary_verbs(resume, facts))

    return VerificationReport(
        fabrication=check_fabrication(resume, truth, extra_numbers),
        inflation=check_inflation(resume, facts, match_threshold, matches=matches),
        coverage=check_coverage(resume, facts, track, match_threshold) if track else None,
        keywords=check_keywords(resume, job, truth) if job is not None else None,
        format=check_format(resume, tex=tex, pdf_path=pdf_path, job_title=title),
        defects=defects,
    )
