"""Unit tests for B3 + Verifier variant (Phase P9 RAG Ablation).

Strictly offline with mocks. Verifies full-context knowledge base injection
into the verifier loop.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.generation.chain import ResumeGenerationChain
from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.b3_full_context import (
    generate_b3_verified,
    load_full_knowledge_base_context,
)
from src.generation.variants.v1_verified import V1Trace


@pytest.fixture
def candidate() -> CandidateProfile:
    return CandidateProfile.from_yaml("data/candidate_profile.yaml")


@pytest.fixture
def job() -> JobPosting:
    return JobPosting(
        title="Data Engineer Intern",
        company="DataFlow Inc",
        raw_description="Looking for Python and SQL intern.",
        technologies=["Python", "SQL"],
    )


def test_b3_verified_generation_mocked(candidate: CandidateProfile, job: JobPosting) -> None:
    """generate_b3_verified injects full KB context into generate_v1."""
    clean_resume = generate_b0(candidate, job, language="en")

    mock_chain = MagicMock(spec=ResumeGenerationChain)
    mock_chain.resolve_language.return_value = "en"
    mock_chain.build_messages.return_value = []
    mock_chain.generate.return_value = clean_resume

    with patch("src.generation.variants.v1_verified.verify_resume") as mock_verify:
        mock_report = MagicMock()
        mock_report.hard_pass = True
        mock_report.fabrication.unsupported = []
        mock_report.inflation.inflated = []
        mock_report.format.failed = []
        mock_report.format.all_passed = True
        mock_verify.return_value = mock_report

        custom_context = "# Custom Knowledge Base Context (12 Docs)"
        resume, trace = generate_b3_verified(
            candidate=candidate,
            job=job,
            chain=mock_chain,
            full_kb_context=custom_context,
            language="en",
        )

        assert isinstance(trace, V1Trace)
        assert trace.final_path == "clean@0"
        assert trace.retrieved_context == custom_context
        assert resume.target_job_title == job.title
