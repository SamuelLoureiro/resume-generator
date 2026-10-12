"""Unit tests for synthetic candidate profiles (Profiles A and B).

Validates schema constraints, facts collection integrity, and verifies that
fallback resumes built from synthetic profiles achieve hard_pass: True.
"""

from __future__ import annotations

from src.data.synthetic_profiles import (
    get_synthetic_fresh_grad,
    get_synthetic_researcher,
)
from src.data.job_posting import JobPosting
from src.generation.chain import build_fallback_tailored_resume
from src.verification.report import verify_resume


def test_synthetic_fresh_grad_schema_and_facts_integrity() -> None:
    profile, facts = get_synthetic_fresh_grad()
    assert profile.contact.full_name == "Alex Rivera"
    assert len(profile.education) == 1
    assert len(profile.experiences) == 1
    assert len(profile.projects) == 2
    assert len(facts.facts) == 7
    # Fact IDs must be unique
    fact_ids = [f.id for f in facts.facts]
    assert len(fact_ids) == len(set(fact_ids))


def test_synthetic_researcher_schema_and_facts_integrity() -> None:
    profile, facts = get_synthetic_researcher()
    assert profile.contact.full_name == "Elena Rostova"
    assert len(profile.education) == 2
    assert len(profile.experiences) == 2
    assert len(profile.projects) == 1
    assert len(facts.facts) == 7
    # Fact IDs must be unique
    fact_ids = [f.id for f in facts.facts]
    assert len(fact_ids) == len(set(fact_ids))


def test_synthetic_fresh_grad_fallback_resume_hard_passes() -> None:
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Software Engineering Intern at TechCorp requiring Python and C++.",
        track="core_swe",
        technologies=["Python", "C++", "Linux", "Docker"],
        keywords=["algorithms", "data structures", "distributed systems"],
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")
    report = verify_resume(resume, profile, facts, job=job, track="core_swe")

    assert report.fabrication.unsupported == [], [c.reason for c in report.fabrication.unsupported]
    assert report.inflation.inflated == [], [i.reason for i in report.inflation.inflated]
    assert report.hard_pass is True


def test_synthetic_researcher_fallback_resume_hard_passes() -> None:
    profile, facts = get_synthetic_researcher()
    job = JobPosting(
        title="Machine Learning Research Intern",
        company="AI Research Lab",
        raw_description="Machine Learning Research Intern at AI Research Lab requiring PyTorch.",
        track="ai",
        technologies=["Python", "PyTorch", "HuggingFace"],
        keywords=["deep learning", "graph neural networks", "nlp"],
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")
    report = verify_resume(resume, profile, facts, job=job, track="ai")

    assert report.fabrication.unsupported == [], [c.reason for c in report.fabrication.unsupported]
    assert report.inflation.inflated == [], [i.reason for i in report.inflation.inflated]
    assert report.hard_pass is True
