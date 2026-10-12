"""Unit tests for the V1 variant pipeline (Phase P8).

Strictly offline with mocked LLM and pipeline dependencies.
Tests multi-turn error-guided regeneration, deterministic repair, and fallback triggers.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.data.candidate import CandidateProfile
from src.data.facts import load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import ResumeHeader, ResumeSkillCategory, TailoredResume
from src.evaluation.claim_judge import ClaimVerdict, ResumeEvaluationPayload
from src.generation.chain import ResumeGenerationChain
from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.v1_verified import V1Trace, generate_v1


@pytest.fixture
def candidate() -> CandidateProfile:
    return CandidateProfile.from_yaml("data/candidate_profile.yaml")


@pytest.fixture
def facts():
    return load_candidate_facts("data/candidate_facts.yaml")


@pytest.fixture
def job() -> JobPosting:
    return JobPosting(
        title="AI Engineer Intern",
        company="NeuroTech",
        raw_description="Looking for Python, PyTorch, C++ intern.",
        technologies=["Python", "C++"],
    )


def test_v1_clean_on_round_0(candidate: CandidateProfile, job: JobPosting, facts) -> None:
    """When the initial generated resume has no defects, V1 terminates immediately at clean@0."""
    # Build clean baseline resume
    clean_resume = generate_b0(candidate, job, language="en")

    mock_chain = MagicMock(spec=ResumeGenerationChain)
    mock_chain.resolve_language.return_value = "en"
    mock_chain.build_messages.return_value = []
    mock_chain.generate.return_value = clean_resume

    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "Guidelines text"

    mock_judge = MagicMock()
    mock_judge.evaluate_resume.return_value = ResumeEvaluationPayload(
        resume_id="test",
        claims=[
            ClaimVerdict(
                bullet_id="exp_0_bullet_0",
                claim_id="c1",
                source_span="developed firmware",
                claim_type="action",
                rationale="Supported by fact",
                matched_fact_ids=["exp_enib_firmware"],
                verdict="grounded",
            )
        ],
    )

    resume, trace = generate_v1(
        candidate=candidate,
        job=job,
        pipeline=mock_pipeline,
        chain=mock_chain,
        judge=mock_judge,
        facts=facts,
        language="en",
    )

    assert trace.final_path == "clean@0"
    assert trace.total_rounds == 1
    assert len(trace.rounds) == 1
    assert trace.rounds[0].hard_pass is True
    assert trace.rounds[0].issues_count == 0
    assert resume.target_job_title == job.title


def test_v1_recovers_on_retry_1(candidate: CandidateProfile, job: JobPosting, facts) -> None:
    """When round 0 has issues, V1 feeds back errors and recovers at clean@1."""
    # Round 0: resume with defective skill
    corrupted_resume = generate_b0(candidate, job, language="en")
    corrupted_resume.skills = [
        ResumeSkillCategory(
            category_name="Cloud",
            skills=["FabricatedCloud123"],
        )
    ]

    # Round 1: clean resume
    clean_resume = generate_b0(candidate, job, language="en")

    mock_chain = MagicMock(spec=ResumeGenerationChain)
    mock_chain.resolve_language.return_value = "en"
    mock_chain.build_messages.return_value = []
    mock_chain.generate.return_value = corrupted_resume
    mock_chain.regenerate_with_feedback.return_value = clean_resume

    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "Guidelines text"

    mock_judge = MagicMock()
    mock_judge.evaluate_resume.return_value = ResumeEvaluationPayload(
        resume_id="test",
        claims=[
            ClaimVerdict(
                bullet_id="exp_0_bullet_0",
                claim_id="c1",
                source_span="developed firmware",
                claim_type="action",
                rationale="Supported by fact",
                matched_fact_ids=["exp_enib_firmware"],
                verdict="grounded",
            )
        ],
    )

    resume, trace = generate_v1(
        candidate=candidate,
        job=job,
        pipeline=mock_pipeline,
        chain=mock_chain,
        judge=mock_judge,
        facts=facts,
        language="en",
        max_retries=2,
    )

    assert trace.final_path == "clean@1"
    assert trace.total_rounds == 2
    assert len(trace.rounds) == 2
    assert trace.rounds[0].hard_pass is False
    assert trace.rounds[1].hard_pass is True
    assert mock_chain.regenerate_with_feedback.call_count == 1


def test_v1_applies_deterministic_repair(candidate: CandidateProfile, job: JobPosting, facts) -> None:
    """When LLM retries still fail, deterministic repair fixes defects and succeeds."""
    # Resume with persistent unsupported skill
    defective_resume = generate_b0(candidate, job, language="en")
    defective_resume.skills = [
        ResumeSkillCategory(
            category_name="DevOps",
            skills=["InventedToolXYZ"],
        )
    ]

    mock_chain = MagicMock(spec=ResumeGenerationChain)
    mock_chain.resolve_language.return_value = "en"
    mock_chain.build_messages.return_value = []
    mock_chain.generate.return_value = defective_resume
    # Regenerations also return defective resume
    mock_chain.regenerate_with_feedback.return_value = defective_resume

    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "Guidelines"

    resume, trace = generate_v1(
        candidate=candidate,
        job=job,
        pipeline=mock_pipeline,
        chain=mock_chain,
        judge=None,
        facts=facts,
        language="en",
        max_retries=2,
    )

    assert trace.final_path == "repaired"
    assert trace.repair_actions_count > 0
    # Repair removed the invented skill
    assert not any("InventedToolXYZ" in cat.skills for cat in resume.skills)


def test_v1_privacy_mandate_no_pii_in_prompts(candidate: CandidateProfile, job: JobPosting, facts) -> None:
    """SEC-01: Verifies that contact info (phone, email) is not present in regeneration prompts."""
    corrupted_resume = generate_b0(candidate, job, language="en")
    corrupted_resume.skills = [
        ResumeSkillCategory(
            category_name="Tools",
            skills=["FakeTool"],
        )
    ]

    mock_chain = ResumeGenerationChain(llm=MagicMock())
    base_messages = mock_chain.build_messages(candidate, job, "Guidelines", "en")

    # Assert no PII in user message
    user_content = base_messages[1].content
    assert candidate.contact.email not in user_content
    assert candidate.contact.phone not in user_content

    # Regenerate call check
    mock_chain.llm.chat.return_value = MagicMock(
        message=MagicMock(content=generate_b0(candidate, job, language="en").model_dump_json())
    )

    history = [(corrupted_resume, "Feedback prompt")]
    repaired_resume = mock_chain.regenerate_with_feedback(candidate, base_messages, history, "en")

    # The header must be deterministically restored after regeneration
    assert repaired_resume.header.email == candidate.contact.email
    assert repaired_resume.header.phone == candidate.contact.phone
