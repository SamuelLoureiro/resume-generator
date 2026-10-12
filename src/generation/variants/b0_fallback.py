"""B0 Variant: Deterministic fallback resume generator (no LLM, no RAG).

Serves as the empirical floor for evaluation. Uses strictly verified candidate data
and deterministic heuristics to produce a tailored resume.
"""

from __future__ import annotations

from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import ResumeLanguageCode, TailoredResume
from src.generation.chain import (
    build_fallback_tailored_resume,
    detect_language_from_text,
)


def generate_b0(
    candidate: CandidateProfile,
    job: JobPosting,
    language: str = "auto",
) -> TailoredResume:
    """Generate a deterministic fallback resume without LLM calls.

    Args:
        candidate: Verified candidate profile.
        job: Target internship posting.
        language: Target language ('auto', 'pt', 'en', 'fr').

    Returns:
        TailoredResume: Complete, deterministic, un-hallucinated resume.
    """
    if language in ("pt", "en", "fr"):
        resolved_lang: ResumeLanguageCode = language  # type: ignore[assignment]
    else:
        resolved_lang = detect_language_from_text(f"{job.title} {job.raw_description}")

    return build_fallback_tailored_resume(
        candidate=candidate,
        job=job,
        language=resolved_lang,
    )
