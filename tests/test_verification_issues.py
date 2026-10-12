"""Unit tests for verification issues collection and normalization (Phase P8).

Strictly offline with synthetic data and mock structures.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import ResumeExperience, TailoredResume
from src.evaluation.claim_judge import ClaimVerdict, ResumeEvaluationPayload
from src.generation.variants.b0_fallback import generate_b0
from src.verification.fabrication import FabricationResult, UnsupportedClaim
from src.verification.format_checks import FormatCheck, FormatResult
from src.verification.inflation import InflatedBullet, InflationResult
from src.verification.issues import (
    VerificationIssue,
    bullet_id_for,
    collect_issues,
    has_fixable_issues,
    has_truth_issues,
    locate_bullet,
    parse_bullet_id,
)
from src.verification.report import VerificationReport


def test_parse_bullet_id() -> None:
    """Correctly parses various bullet ID syntaxes from judge outputs."""
    assert parse_bullet_id("exp_0_bullet_1") == ("experience", 0, 1)
    assert parse_bullet_id("experience_2_bullet_0") == ("experience", 2, 0)
    assert parse_bullet_id("proj_1_bullet_3") == ("project", 1, 3)
    assert parse_bullet_id("project_0_b2") == ("project", 0, 2)
    assert parse_bullet_id("summary") is None
    assert parse_bullet_id("invalid") is None


def test_bullet_id_for_and_locate_bullet() -> None:
    """Canonical bullet id formatting and reverse text lookup."""
    assert bullet_id_for("experience", 1, 2) == "exp_1_bullet_2"
    assert bullet_id_for("project", 0, 1) == "proj_0_bullet_1"

    resume = MagicMock(spec=TailoredResume)
    exp_mock = MagicMock(spec=ResumeExperience)
    exp_mock.bullets = ["First bullet", "Second bullet targeted"]
    resume.experiences = [exp_mock]
    resume.projects = []

    assert locate_bullet(resume, "Second bullet targeted") == "exp_0_bullet_1"
    assert locate_bullet(resume, "Non-existent bullet") is None


def test_collect_issues_with_deterministic_and_judge_payloads() -> None:
    """Flattens deterministic checks and claim judge outputs into ordered, unique issues."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme Corp", raw_description="Internship")

    resume = generate_b0(profile, job, language="en")

    # Synthetic report with 1 fabrication, 1 inflation, 1 format fail
    report = VerificationReport(
        fabrication=FabricationResult(
            checked={"a": 5, "b": 2, "c": 3},
            unsupported=[
                UnsupportedClaim(
                    sub="a",
                    kind="skill",
                    text="TensorRT",
                    reason="'TensorRT' (skills/AI) is not in profile",
                )
            ],
        ),
        inflation=InflationResult(
            inflated=[
                InflatedBullet(
                    bullet="Architected microservices.",
                    verb="Architected",
                    verb_level=4,
                    fact_id="exp_asimov_leadership",
                    scope_ceiling=2,
                    reason="Verb level 4 exceeds ceiling 2",
                )
            ]
        ),
        format=FormatResult(
            checks=[
                FormatCheck(name="no_empty_entries", status="pass"),
                FormatCheck(name="urls", status="fail", detail="Invalid URL"),
            ]
        ),
    )

    # Synthetic judge payload
    judge_payload = ResumeEvaluationPayload(
        resume_id="test_res",
        claims=[
            ClaimVerdict(
                bullet_id="exp_0_bullet_0",
                claim_id="claim_1",
                source_span="Spearheaded distributed computing cluster",
                claim_type="action",
                rationale="No fact supports building distributed computing cluster",
                matched_fact_ids=[],
                verdict="unsupported_claim",
            ),
            ClaimVerdict(
                bullet_id="exp_0_bullet_1",
                claim_id="claim_2",
                source_span="Led the team",
                claim_type="scope",
                rationale="Scope ceiling is level 2",
                matched_fact_ids=["exp_asimov_leadership"],
                extracted_scope_level=4,
                verdict="inflated_scope",
            ),
        ],
    )

    issues = collect_issues(
        resume=resume,
        report=report,
        facts=facts,
        judge_payload=judge_payload,
    )

    assert len(issues) == 5
    assert issues[0].kind == "unsupported_skill"
    assert issues[0].text == "TensorRT"
    assert issues[1].kind == "inflated_verb"
    assert issues[2].kind == "judge_unsupported"
    assert issues[2].location == "exp_0_bullet_0"
    assert issues[3].kind == "judge_inflated"
    assert issues[4].kind == "format"

    assert has_truth_issues(issues) is True
    assert has_fixable_issues(issues) is True


def test_collect_issues_with_judge_error() -> None:
    """When judge fails, collect_issues creates fail-closed judge_unavailable issue."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme Corp", raw_description="Internship")
    resume = generate_b0(profile, job, language="en")

    report = VerificationReport(
        fabrication=FabricationResult(),
        inflation=InflationResult(),
        format=FormatResult(),
    )

    issues = collect_issues(
        resume=resume,
        report=report,
        facts=facts,
        judge_payload=None,
        judge_error="API quota exhausted",
    )

    assert len(issues) == 1
    assert issues[0].kind == "judge_unavailable"
    assert issues[0].llm_fixable is False
    assert has_truth_issues(issues) is True
    assert has_fixable_issues(issues) is False
