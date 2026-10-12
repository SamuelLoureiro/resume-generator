"""Unit and golden regression tests for Phase B defect checks (B1–B5) and Phase C selection."""

from __future__ import annotations

import pytest

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import ResumeExperience, ResumeProject, ResumeSkillCategory, TailoredResume
from src.data.synthetic_profiles import get_synthetic_fresh_grad
from src.generation.chain import build_fallback_tailored_resume
from src.verification.defect_checks import (
    check_fact_fusion,
    check_job_phrase_echo,
    check_summary_lint,
    check_summary_verbs,
)
from src.verification.repair import repair_resume
from src.verification.report import verify_resume
from src.verification.text_utils import select_relevant_coursework


@pytest.fixture
def base_setup():
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Edge AI and Embedded Software Intern",
        company="Inalfa Roof Systems",
        raw_description="Develop lightweight neural networks for automotive ECUs running ARM Cortex-M4 and CAN bus.",
        track="embedded",
        technologies=["C++", "C", "CAN Bus", "TinyML", "FreeRTOS", "ARM Cortex-M4"],
        keywords=["microcontrollers", "real-time systems", "firmware", "signal processing"],
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")
    return profile, facts, job, resume


# ---------------------------------------------------------------------------
# B1: SUMMARY_LINT Tests
# ---------------------------------------------------------------------------

def test_summary_lint_flags_meta_words(base_setup) -> None:
    profile, facts, job, resume = base_setup
    # Inject meta-words in summary and bullet
    resume.objective_or_summary = "Candidate with verified track record in embedded systems."
    resume.experiences[0].bullets[0] = "Developed pipeline for data processing grounded in fact."

    issues = check_summary_lint(resume, profile)
    kinds = [i["kind"] for i in issues]
    texts = [i["text"].lower() for i in issues]

    assert "summary_lint" in kinds
    assert "verified" in texts
    assert "grounded" in texts or "fact" in texts


def test_summary_lint_exempts_profile_skills(base_setup) -> None:
    profile, facts, job, resume = base_setup
    # If profile has a technology like 'Docker' or 'Git', using it does not trigger lint
    resume.objective_or_summary = "Engineering student experienced in C++ and Docker."
    issues = check_summary_lint(resume, profile)
    assert len(issues) == 0


def test_summary_lint_deterministic_repair(base_setup) -> None:
    profile, facts, job, resume = base_setup
    resume.objective_or_summary = "Student with verified experience in embedded C++."
    report = verify_resume(resume, profile, facts, job=job)
    assert not report.defect_free
    assert any(d["kind"] == "summary_lint" for d in report.defects)

    from src.verification.issues import collect_issues
    issues = collect_issues(resume, report, facts)
    repaired, log = repair_resume(resume, issues, profile, facts, job=job)

    # Repaired summary must no longer contain the meta-word
    assert "verified" not in repaired.objective_or_summary.lower()
    assert "embedded c++" in repaired.objective_or_summary.lower() or "student" in repaired.objective_or_summary.lower()


# ---------------------------------------------------------------------------
# B2: JOB_PHRASE_ECHO Tests
# ---------------------------------------------------------------------------

def test_job_phrase_echo_flags_verbatim_job_text(base_setup) -> None:
    profile, facts, job, resume = base_setup
    # Job description has: "Develop lightweight neural networks for automotive ECUs"
    # Inject phrase into summary that candidate facts do not have
    resume.objective_or_summary = "Seeking to develop lightweight neural networks for automotive ECUs."

    issues = check_job_phrase_echo(resume, job, profile, facts)
    assert len(issues) >= 1
    assert any(i["kind"] == "job_phrase_echo" for i in issues)
    assert any("lightweight" in i["text"] or "neural" in i["text"] for i in issues)
    assert "rewrite using candidate's own fact wording" in issues[0]["detail"]


def test_job_phrase_echo_passes_for_candidate_own_facts(base_setup) -> None:
    profile, facts, job, resume = base_setup
    # Wording coming straight from candidate's verified background
    resume.objective_or_summary = (
        "Engineering student applying technical fundamentals in C++ and embedded systems."
    )
    issues = check_job_phrase_echo(resume, job, profile, facts)
    assert len(issues) == 0


# ---------------------------------------------------------------------------
# B3: FACT_FUSION Golden Regression Tests
# ---------------------------------------------------------------------------

def test_golden_asimov_fact_fusion_detected() -> None:
    """Golden regression test: fused Asimov leadership and awards in one sentence MUST be detected."""
    real_facts = load_candidate_facts()

    # Fused sentence combining Data Science department creation with Area of the Month
    fused_resume = TailoredResume(
        target_job_title="Embedded Software Intern",
        target_company="Inalfa",
        objective_or_summary=(
            "Promoted to Mobile Area Manager and spearheaded the creation of the Data Science "
            "department, winning Area of the Month for team performance."
        ),
        education=[],
        experiences=[],
        projects=[],
        skills=[],
        languages=[],
        certifications=[],
    )

    issues = check_fact_fusion(fused_resume, real_facts)
    assert len(issues) >= 1, "Fact fusion was NOT detected on the fused Asimov sentence!"
    assert issues[0]["kind"] == "fact_fusion"
    assert "exp_asimov_leadership" in issues[0]["fact_id"]
    assert "Split into two sentences or keep only one fact" in issues[0]["detail"]


def test_golden_asimov_separate_sentences_pass() -> None:
    """Golden regression test: leadership and awards in separate sentences MUST pass."""
    real_facts = load_candidate_facts()

    # Two separate sentences respecting entity-subject binding
    clean_resume = TailoredResume(
        target_job_title="Embedded Software Intern",
        target_company="Inalfa",
        objective_or_summary=(
            "Promoted to Mobile Area Manager leading 5+ developers, and spearheaded the creation "
            "of the Data Science department. Led the mobile development team to win Area of the Month."
        ),
        education=[],
        experiences=[],
        projects=[],
        skills=[],
        languages=[],
        certifications=[],
    )

    issues = check_fact_fusion(clean_resume, real_facts)
    assert len(issues) == 0, f"False positive fact fusion detected on clean separate sentences: {issues}"


# ---------------------------------------------------------------------------
# B5: SUMMARY_VERB Tests
# ---------------------------------------------------------------------------

def test_summary_verbs_flags_inflated_verb() -> None:
    real_facts = load_candidate_facts()
    # Find a fact with ceiling 2 or 1
    # Candidate participated in Custom PCB Design (exp_enib_system_codesign, ceiling 2)
    # Claiming "Architected" or "Spearheaded" exceeds ceiling
    inflated_resume = TailoredResume(
        target_job_title="Hardware Intern",
        target_company="TechLab",
        objective_or_summary=(
            "Engineering student who architected custom PCB schematic and SPI communication protocols."
        ),
        education=[],
        experiences=[],
        projects=[],
        skills=[],
        languages=[],
        certifications=[],
    )

    issues = check_summary_verbs(inflated_resume, real_facts)
    assert len(issues) >= 1
    assert issues[0]["kind"] == "inflated_verb"
    assert "architected" in issues[0]["text"].lower()


# ---------------------------------------------------------------------------
# Phase C: Coursework Selection Tests
# ---------------------------------------------------------------------------

def test_select_relevant_coursework_embedded_vs_backend() -> None:
    courses = [
        "Business Administration",
        "Microcontrollers & Embedded Systems",
        "Quantum Physics",
        "Real-Time Operating Systems",
        "Distributed Systems & Cloud Computing",
        "Digital Signal Processing",
        "Web Development & CSS",
        "Relational Databases & SQL",
    ]

    # Embedded / Edge AI Job
    embedded_job = JobPosting(
        title="Edge AI and MCU Firmware Intern",
        company="Inalfa",
        raw_description="Firmware development for microcontrollers, FreeRTOS, and real-time DSP filters.",
        technologies=["C", "ARM Cortex-M4", "RTOS"],
        keywords=["microcontrollers", "dsp", "embedded"],
    )
    embedded_selected = select_relevant_coursework(courses, embedded_job, max_courses=3)
    assert "Microcontrollers & Embedded Systems" in embedded_selected
    assert "Real-Time Operating Systems" in embedded_selected
    assert "Digital Signal Processing" in embedded_selected
    assert "Business Administration" not in embedded_selected
    assert "Web Development & CSS" not in embedded_selected

    # Backend Engineering Job
    backend_job = JobPosting(
        title="Backend Software Engineering Intern",
        company="Stripe",
        raw_description="Design distributed backend microservices and database storage pipelines.",
        technologies=["Python", "PostgreSQL", "Kafka"],
        keywords=["distributed systems", "databases", "sql"],
    )
    backend_selected = select_relevant_coursework(courses, backend_job, max_courses=3)
    assert "Distributed Systems & Cloud Computing" in backend_selected
    assert "Relational Databases & SQL" in backend_selected
    assert "Quantum Physics" not in backend_selected


# ---------------------------------------------------------------------------
# Phase C: Fact Selection & Priority Weighting Tests
# ---------------------------------------------------------------------------

def test_rank_facts_for_job_priority2_outranks_priority1() -> None:
    real_facts = load_candidate_facts()
    embedded_job = JobPosting(
        title="Automotive Edge AI Intern",
        company="Inalfa Roof Systems",
        raw_description="Deploy TinyML on microcontroller ECUs with CAN bus communications.",
        track="embedded",
        technologies=["C++", "CAN Bus", "TinyML", "ARM Cortex-M4"],
        keywords=["microcontrollers", "automotive", "ecu"],
    )

    ranked = real_facts.rank_facts_for_job(embedded_job, track="embedded")
    ranked_ids = [f.id for f in ranked]

    # Priority-2 facts matching embedded/ai tracks and awards MUST rank highly
    # and not be dropped
    assert "exp_asimov_mobile_area_of_month" in ranked_ids[:10]
    assert "exp_asimov_member_of_month" in ranked_ids[:12]
