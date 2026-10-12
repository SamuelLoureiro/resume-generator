"""Offline unit tests for the atomic claim-level judge.

Validates that:
- LaTeX markup and comments are stripped cleanly before LLM submission.
- Schema validation enforces fail-closed behavior (empty claims reject, citation required for grounded).
- Mechanical scope checks override LLM leniency when extracted scope exceeds fact ceiling.
- ClaimLevelJudge executes reliably offline with mocked LLM responses.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from src.data.synthetic_profiles import get_synthetic_fresh_grad
from src.data.job_posting import JobPosting
from src.evaluation.claim_judge import (
    ClaimLevelJudge,
    ClaimVerdict,
    ResumeEvaluationPayload,
    format_facts_for_judge,
    format_resume_bullets_for_judge,
    strip_latex_markup,
)
from src.generation.chain import build_fallback_tailored_resume


def test_strip_latex_markup() -> None:
    raw_latex = r"Developed \textbf{core features} with 90\% accuracy and \% & \_ \href{https://example.com}{Live Demo}. % Injected label leak"
    clean = strip_latex_markup(raw_latex)

    assert "% Injected label leak" not in clean
    assert r"\textbf" not in clean
    assert "Live Demo" in clean
    assert "90%" in clean
    assert "core features" in clean


def test_schema_fail_closed_on_empty_claims() -> None:
    with pytest.raises(ValueError, match="empty claims list"):
        ResumeEvaluationPayload.model_validate({
            "resume_id": "test_1",
            "claims": [],
        })


def test_schema_requires_fact_citation_for_grounded_verdict() -> None:
    with pytest.raises(ValueError, match="marked grounded without fact citation"):
        ResumeEvaluationPayload.model_validate({
            "resume_id": "test_1",
            "claims": [
                {
                    "bullet_id": "b_1",
                    "claim_id": "c_1",
                    "source_span": "Built API",
                    "claim_type": "action",
                    "rationale": "It seems fine.",
                    "evidence_quote": None,
                    "matched_fact_ids": [],  # Empty citations not allowed for grounded!
                    "extracted_scope_level": 3,
                    "verdict": "grounded",
                }
            ],
        })


def test_format_facts_and_bullets_for_judge() -> None:
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Software Engineering Intern.",
        track="core_swe",
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")

    facts_str = format_facts_for_judge(facts)
    bullets_str = format_resume_bullets_for_judge(resume)

    assert "edu_rivera_cs" in facts_str
    assert "proj_rivera_queue_dev" in facts_str
    assert '[BULLET id="summary"]' in bullets_str
    assert '[BULLET id="exp_0_bullet_0"]' in bullets_str


def test_claim_level_judge_offline_mock_evaluation() -> None:
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Software Engineering Intern.",
        track="core_swe",
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")

    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_payload = {
        "resume_id": "alex_rivera_clean",
        "claims": [
            {
                "bullet_id": "exp_0_bullet_0",
                "claim_id": "claim_1",
                "source_span": "Conducted weekly lab sessions for 40+ undergraduate students",
                "claim_type": "action",
                "rationale": "Directly stated in exp_rivera_ta_teaching.",
                "evidence_quote": "Conducted weekly lab sessions for 40+ undergraduate students",
                "matched_fact_ids": ["exp_rivera_ta_teaching"],
                "extracted_scope_level": 3,
                "verdict": "grounded",
            }
        ],
    }
    mock_response.message.content = json.dumps(mock_payload)
    mock_llm.chat.return_value = mock_response

    judge = ClaimLevelJudge(llm=mock_llm)
    result = judge.evaluate_resume("alex_rivera_clean", resume, facts)

    assert result.resume_id == "alex_rivera_clean"
    assert len(result.claims) == 1
    assert result.claims[0].verdict == "grounded"
    assert not result.has_unsupported


def test_mechanical_scope_ceiling_override() -> None:
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Software Engineering Intern.",
        track="core_swe",
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")

    # edu_rivera_cs has ceiling 1 (participated).
    # If LLM marks a level 4 (led) claim as "grounded", our mechanical check must override to "inflated_scope"!
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_payload = {
        "resume_id": "scope_test",
        "claims": [
            {
                "bullet_id": "edu_0",
                "claim_id": "claim_1",
                "source_span": "Led university curriculum",
                "claim_type": "scope",
                "rationale": "Claimed leadership over education.",
                "evidence_quote": "Enrolled in B.Sc. in Computer Science",
                "matched_fact_ids": ["edu_rivera_cs"],
                "extracted_scope_level": 4,  # Level 4 > ceiling 1!
                "verdict": "grounded",       # LLM erroneously lenient
            }
        ],
    }
    mock_response.message.content = json.dumps(mock_payload)
    mock_llm.chat.return_value = mock_response

    judge = ClaimLevelJudge(llm=mock_llm)
    result = judge.evaluate_resume("scope_test", resume, facts)

    assert result.claims[0].verdict == "inflated_scope"
    assert "Mechanical override" in result.claims[0].rationale
    assert result.has_unsupported is True


def test_dry_run_execution_opens_zero_sockets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Verify that offline evaluation and deterministic verification open zero network sockets."""
    import socket
    from scripts.run_judge_validation import (
        load_clean_validation_dataset,
        generate_corrupted_dataset,
        evaluate_deterministic,
    )

    def forbidden_socket(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("Network socket connection attempted during offline evaluation!")

    monkeypatch.setattr(socket, "socket", forbidden_socket)

    clean_resumes, profiles, facts_map, jobs_map, tracks_map = load_clean_validation_dataset()
    assert len(clean_resumes) == 10

    corrupted_list, ledger = generate_corrupted_dataset(clean_resumes, profiles, facts_map, seed=42)
    assert len(corrupted_list) >= 10

    det_samples = []
    for r_id, res in clean_resumes.items():
        det_samples.append((r_id, res, profiles[r_id], facts_map[r_id], jobs_map[r_id], tracks_map[r_id], None))
    for c in corrupted_list[:10]:
        base_id = c.resume_id.rsplit("_", 1)[0]
        det_samples.append((c.resume_id, c.resume, profiles[base_id], c.active_facts, jobs_map[base_id], tracks_map[base_id], c.injections[0]))

    results = evaluate_deterministic(det_samples)
    assert results["clean_false_positives"] == 0

