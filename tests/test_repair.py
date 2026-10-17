"""Unit tests for deterministic repair module (Phase P8, Variant V1).

Strictly offline, verifying deterministic surgical corrections on corrupted resume instances.
"""

from __future__ import annotations

from src.data.candidate import CandidateProfile
from src.data.facts import load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeExperience,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.generation.variants.b0_fallback import generate_b0
from src.verification.issues import VerificationIssue
from src.verification.repair import RepairLog, repair_resume
from src.verification.report import verify_resume


def test_repair_unsupported_skills() -> None:
    """Purges unverified skills while preserving legitimate skills."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme", raw_description="Internship")

    resume = generate_b0(profile, job, language="en")
    # Corrupt skills with invented technologies
    resume.skills = [
        ResumeSkillCategory(
            category_name="Programming Languages",
            skills=["Python", "C++", "QuantumLang9000", "InventedScript"],
        ),
        ResumeSkillCategory(
            category_name="Cloud",
            skills=["FakeCloudService"],
        ),
    ]

    issues = [
        VerificationIssue(
            kind="unsupported_skill",
            source="deterministic",
            location="skills/Programming Languages",
            text="QuantumLang9000",
            detail="Not in profile",
        ),
        VerificationIssue(
            kind="unsupported_skill",
            source="deterministic",
            location="skills/Programming Languages",
            text="InventedScript",
            detail="Not in profile",
        ),
        VerificationIssue(
            kind="unsupported_skill",
            source="deterministic",
            location="skills/Cloud",
            text="FakeCloudService",
            detail="Not in profile",
        ),
    ]

    repaired, log = repair_resume(resume, issues, profile, facts)

    assert log.total_actions == 3
    # Allowed skills remain
    assert repaired.skills[0].skills == ["Python", "C++"]
    # Empty category was dropped
    assert len(repaired.skills) == 1


def test_repair_dates_titles_and_fabricated_organization() -> None:
    """Overwrites corrupted dates and titles, and drops completely invented organizations."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme", raw_description="Internship")

    resume = generate_b0(profile, job, language="en")
    resume.experiences = [
        ResumeExperience(
            title="Senior VP of AI (Invented Title)",
            organization="Asimov Jr.",
            period="01/2020 - 12/2026 (Invented Period)",
            bullets=["Legitimate bullet 1"],
            technologies=["Python"],
        ),
        ResumeExperience(
            title="NASA Lead Astronaut",
            organization="NASA Space Station Inc",
            period="2024 - Present",
            bullets=["Flew to Mars"],
            technologies=["RocketFuel"],
        ),
    ]

    issues = [
        VerificationIssue(
            kind="entity_mismatch",
            source="deterministic",
            location="experience/Asimov Jr.",
            text="Senior VP of AI",
            detail="Title does not match profile",
        ),
        VerificationIssue(
            kind="entity_mismatch",
            source="deterministic",
            location="experience/NASA Space Station Inc",
            text="NASA Space Station Inc",
            detail="Organization not in profile",
        ),
    ]

    repaired, log = repair_resume(resume, issues, profile, facts)

    assert len(repaired.experiences) == 1
    asimov = repaired.experiences[0]
    assert asimov.organization == "Asimov Jr."
    assert asimov.title == "Mobile Development & Data Science Manager"
    assert asimov.period == "12/2023 - 09/2025"


def test_repair_defective_bullets_and_restore_fallback() -> None:
    """Removes defective bullets and restores profile bullets if entry becomes empty."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme", raw_description="Internship")

    resume = generate_b0(profile, job, language="en")
    resume.experiences = [
        ResumeExperience(
            title="Mobile Development & Data Science Manager",
            organization="Asimov Jr.",
            period="12/2023 - 09/2025",
            bullets=[
                "Architected supercomputer cluster with 9999 nodes.",  # defective
            ],
            technologies=["Flutter", "Python"],
        )
    ]

    issues = [
        VerificationIssue(
            kind="judge_unsupported",
            source="judge",
            location="exp_0_bullet_0",
            text="Architected supercomputer cluster with 9999 nodes.",
            detail="Unsupported claim and number",
        )
    ]

    repaired, log = repair_resume(resume, issues, profile, facts)

    assert len(repaired.experiences) == 1
    # Fallback bullets restored from profile
    assert len(repaired.experiences[0].bullets) > 0
    assert "supercomputer" not in repaired.experiences[0].bullets[0]
    assert any(a.action == "restore_profile_bullets" for a in log.actions)


def test_repair_summary_reset() -> None:
    """Resets objective/summary to deterministic template if flagged with unsupported claims."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Software Intern", company="Acme", raw_description="Internship")

    resume = generate_b0(profile, job, language="en")
    resume.objective_or_summary = "Invented PhD candidate with 15 years of industry experience at Google."

    issues = [
        VerificationIssue(
            kind="unsupported_number",
            source="deterministic",
            location="summary",
            text="15",
            detail="Unsupported number",
        )
    ]

    repaired, log = repair_resume(resume, issues, profile, facts)

    assert any(a.action == "reset_to_deterministic_objective" for a in log.actions)
    assert "15" not in (repaired.objective_or_summary or "")
    assert "Acme" in (repaired.objective_or_summary or "")


def test_repair_backfills_underfilled_bullets_and_projects() -> None:
    """Verifies that repair backfills verified bullets when count < 2 and backfills projects up to 3."""
    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Embedded Software Intern", company="Acme", raw_description="C/C++ firmware")

    resume = generate_b0(profile, job, language="en")
    # Simulate an experience with only 1 bullet and only 1 project
    resume.experiences[0].bullets = ["Single bullet"]
    resume.projects = [resume.projects[0]]

    repaired, log = repair_resume(resume, [], profile, facts)

    # Experience backfilled to at least 2 bullets
    assert len(repaired.experiences[0].bullets) >= 2
    # Projects backfilled up to 3
    assert len(repaired.projects) == 3
    assert any(a.action == "restore_profile_project" for a in log.actions)


def test_repair_french_resume_preserves_single_language() -> None:
    """Verifies that repairing a French resume does not mix in English profile bullets."""
    from src.verification.report import verify_resume

    profile = CandidateProfile.from_yaml("data/candidate_profile.yaml")
    facts = load_candidate_facts("data/candidate_facts.yaml")
    job = JobPosting(title="Stage Ingénieur Embarqué", company="Thales", raw_description="Stage C/C++")

    resume = generate_b0(profile, job, language="fr")
    resume.objective_or_summary = (
        "Étudiant en ingénierie informatique spécialisé dans le développement de micrologiciels en C et FreeRTOS."
    )
    for edu in resume.education:
        edu.highlights = ["Cours pertinents : Architecture des ordinateurs, Systèmes temps réel"]
    resume.experiences = [
        ResumeExperience(
            title="Embedded Systems Researcher (Team Professionalizing Project)",
            organization="ENIB",
            period="09/2025 - 12/2025",
            bullets=[
                "Développé un micrologiciel en C sous FreeRTOS incluant un protocole SPI maître-esclave déterministe.",
                "Conçu un supercalculateur quantique avec 9999 cœurs.",  # defective
            ],
            technologies=["C", "FreeRTOS"],
        )
    ]
    resume.projects = [
        ResumeProject(
            name="CAN Bus Sensor Network",
            bullets=[
                "Intégré le nœud de capteur IMU dans l’architecture de bus CAN distribuée en C/C++.",
            ],
            technologies=["C / C++", "CAN Bus"],
        )
    ]

    issues = [
        VerificationIssue(
            kind="unsupported_number",
            source="deterministic",
            location="exp_0_bullet_1",
            text="9999",
            detail="Unsupported number",
        )
    ]

    repaired, _ = repair_resume(resume, issues, profile, facts, job=job)
    report = verify_resume(repaired, profile, facts, job=job)

    assert len(repaired.experiences[0].bullets) == 1
    assert report.hard_pass is True

