"""Unit tests for generation variants (B0, B1, B3).

All tests run strictly offline with mocks or synthetic data.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeHeader,
    TailoredResume,
)
from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.b1_hybrid_rag import generate_b1
from src.generation.variants.b3_full_context import (
    generate_b3,
    load_full_knowledge_base_context,
)


@pytest.fixture
def mock_candidate() -> CandidateProfile:
    """Load default verified candidate profile."""
    return CandidateProfile.from_yaml("data/candidate_profile.yaml")


@pytest.fixture
def sample_job() -> JobPosting:
    """Create a minimal sample job posting."""
    return JobPosting(
        title="ML Engineer Intern",
        company="Test AI Corp",
        location="Remote",
        work_model="Remote",
        raw_description="Looking for an ML engineer intern experienced with Python and PyTorch.",
        technologies=["Python", "PyTorch"],
    )


def test_b0_generation(mock_candidate: CandidateProfile, sample_job: JobPosting) -> None:
    """B0 generates a valid deterministic resume without any external calls."""
    resume = generate_b0(candidate=mock_candidate, job=sample_job, language="en")
    assert isinstance(resume, TailoredResume)
    assert resume.target_job_title == sample_job.title
    assert resume.target_company == sample_job.company
    assert len(resume.education) > 0
    assert len(resume.skills) > 0


def test_load_full_knowledge_base_context() -> None:
    """B3 context loader aggregates all 12 documents into a structured markdown block."""
    context = load_full_knowledge_base_context()
    assert isinstance(context, str)
    assert len(context) > 1000
    assert "Complete Recruitment & Resume Best Practices Knowledge Base" in context
    assert "01_resume_structure_for_internships" in context or "Structure" in context
    assert "hr_recruitment" in context


def test_b1_generation_mocked(mock_candidate: CandidateProfile, sample_job: JobPosting) -> None:
    """B1 retrieves context and calls ResumeGenerationChain."""
    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "Retrieved Guideline Chunk 1\nRetrieved Guideline Chunk 2"

    mock_resume = TailoredResume(
        header=ResumeHeader(
            full_name=mock_candidate.contact.full_name,
            email=mock_candidate.contact.email,
            phone=mock_candidate.contact.phone,
            location=mock_candidate.contact.location,
        ),
        target_job_title=sample_job.title,
        target_company=sample_job.company,
        objective_or_summary="Summary",
    )

    mock_chain = MagicMock()
    mock_chain.generate.return_value = mock_resume

    resume, context = generate_b1(
        candidate=mock_candidate,
        job=sample_job,
        pipeline=mock_pipeline,
        chain=mock_chain,
        top_k=3,
        language="en",
    )

    assert resume == mock_resume
    assert "Retrieved Guideline" in context
    mock_pipeline.get_context_for_job.assert_called_once_with(job=sample_job, top_k=3)
    mock_chain.generate.assert_called_once_with(
        candidate=mock_candidate,
        job=sample_job,
        retrieved_guidelines=context,
        allow_fallback=False,
        language="en",
    )


def test_b3_generation_mocked(mock_candidate: CandidateProfile, sample_job: JobPosting) -> None:
    """B3 passes full KB context without retrieval to ResumeGenerationChain."""
    mock_resume = TailoredResume(
        header=ResumeHeader(
            full_name=mock_candidate.contact.full_name,
            email=mock_candidate.contact.email,
            phone=mock_candidate.contact.phone,
            location=mock_candidate.contact.location,
        ),
        target_job_title=sample_job.title,
        target_company=sample_job.company,
        objective_or_summary="Summary",
    )

    mock_chain = MagicMock()
    mock_chain.generate.return_value = mock_resume

    fake_full_kb = "FULL KNOWLEDGE BASE CONTEXT"
    resume, context = generate_b3(
        candidate=mock_candidate,
        job=sample_job,
        chain=mock_chain,
        full_kb_context=fake_full_kb,
        language="en",
    )

    assert resume == mock_resume
    assert context == fake_full_kb
    mock_chain.generate.assert_called_once_with(
        candidate=mock_candidate,
        job=sample_job,
        retrieved_guidelines=fake_full_kb,
        allow_fallback=False,
        language="en",
    )
