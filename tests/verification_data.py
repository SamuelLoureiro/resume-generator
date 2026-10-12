"""Synthetic ground truth and resumes shared by the verification tests.

Everything here is invented (no real candidate data) so the unit tests of the
verifiers do not depend on ``data/candidate_profile.yaml``.
"""

from __future__ import annotations

from src.data.candidate import (
    Certification,
    CandidateProfile,
    ContactInfo,
    Education,
    Experience,
    Language,
    Project,
    Skills,
)
from src.data.facts import AtomicFact, CandidateFacts
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)


def make_profile() -> CandidateProfile:
    """Invented candidate used across the verification tests."""
    return CandidateProfile(
        contact=ContactInfo(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="+33 7 11 22 33 44",
            location="Paris, France",
            linkedin_url="https://linkedin.com/in/jane",
            github_url="https://github.com/jane",
        ),
        education=[
            Education(
                institution="University of Paris",
                degree="BSc Computer Science",
                start_date="09/2021",
                end_date="06/2024",
                relevant_coursework=["Algorithms", "Databases"],
            )
        ],
        experiences=[
            Experience(
                title="Backend Intern",
                organization="Acme Corp",
                start_date="06/2023",
                end_date="09/2023",
                bullets=["Built REST endpoints for a billing service."],
                technologies=["Python", "PostgreSQL"],
            ),
            Experience(
                title="Research Assistant",
                organization="Beta Labs",
                start_date="01/2024",
                end_date="Present",
                current=True,
                bullets=["Led a team of 4 students."],
                technologies=["PyTorch"],
            ),
        ],
        projects=[
            Project(
                name="Task API",
                description="Task management service.",
                url="https://github.com/jane/task-api",
                bullets=["Developed a task management API with FastAPI and Docker."],
                technologies=["FastAPI", "Docker"],
            ),
            Project(name="Notes", description="Notes app.", url="", technologies=["Flutter"]),
        ],
        skills=Skills(
            programming_languages=["Python", "C / C++"],
            frameworks_and_libraries=["FastAPI", "Scikit-Learn"],
            databases=["PostgreSQL"],
            tools_and_platforms=["Docker", "Git / GitHub"],
            soft_skills=["Teamwork"],
        ),
        languages=[
            Language(language="English", proficiency="Advanced (C1)"),
            Language(language="Portuguese", proficiency="Native"),
        ],
        certifications=[
            Certification(name="AWS Cloud Practitioner", issuer="Amazon", issue_date="05/2024")
        ],
    )


def make_facts() -> CandidateFacts:
    """Invented atomic facts matching :func:`make_profile`."""
    return CandidateFacts(
        facts=[
            AtomicFact(
                id="acme_api",
                source="experience.acme_corp.bullet_1",
                text="Built REST endpoints for an internal billing service using Python and PostgreSQL, cutting report time by 40%.",
                scope_ceiling=3,
                tracks=["backend"],
                priority=1,
                metrics=["40%"],
                tags=["python", "postgresql", "rest-api"],
            ),
            AtomicFact(
                id="acme_review",
                source="experience.acme_corp.bullet_2",
                text="Participated in code reviews for the billing team.",
                scope_ceiling=1,
                tracks=["backend"],
                priority=2,
            ),
            AtomicFact(
                id="beta_lead",
                source="experience.beta_labs.bullet_1",
                text="Led a team of 4 students running annotation experiments.",
                scope_ceiling=4,
                tracks=["ai"],
                priority=1,
                metrics=["4 students"],
                tags=["leadership", "annotation"],
            ),
            AtomicFact(
                id="task_api",
                source="project.task_api.bullet_1",
                text="Developed a task management API with FastAPI and Docker.",
                scope_ceiling=3,
                tracks=["backend"],
                priority=1,
                tags=["fastapi", "docker"],
            ),
            AtomicFact(
                id="notes_app",
                source="project.notes.bullet_1",
                text="Built a small notes application.",
                scope_ceiling=3,
                tracks=["general"],
                priority=3,
                tags=["flutter"],
            ),
        ]
    )


def make_resume(**overrides: object) -> TailoredResume:
    """A clean resume consistent with :func:`make_profile` and :func:`make_facts`.

    Args:
        **overrides: Fields of :class:`TailoredResume` to replace.

    Returns:
        TailoredResume: Resume that passes every deterministic check.
    """
    base: dict[str, object] = {
        "target_job_title": "Backend Software Intern",
        "target_company": "Globex",
        "header": ResumeHeader(
            full_name="Jane Doe",
            email="jane@example.com",
            phone="+33 7 11 22 33 44",
            location="Paris, France",
            linkedin_url="https://linkedin.com/in/jane",
            github_url="https://github.com/jane",
        ),
        "objective_or_summary": "Computer science student focused on backend services and APIs.",
        "education": [
            ResumeEducation(
                institution="University of Paris",
                degree="BSc Computer Science",
                period="09/2021 - 06/2024",
                highlights=["Relevant Coursework: Algorithms, Databases"],
            )
        ],
        "experiences": [
            ResumeExperience(
                title="Backend Intern",
                organization="Acme Corp",
                period="06/2023 - 09/2023",
                bullets=[
                    "Built REST APIs for an internal billing service using Python and PostgreSQL, cutting report time by 40%.",
                    "Participated in code reviews for the billing team.",
                ],
                technologies=["Python", "PostgreSQL"],
            ),
            ResumeExperience(
                title="Research Assistant",
                organization="Beta Labs",
                period="01/2024 - Present",
                bullets=["Led a team of 4 students running annotation experiments."],
                technologies=["PyTorch"],
            ),
        ],
        "projects": [
            ResumeProject(
                name="Task API",
                url="https://github.com/jane/task-api",
                bullets=["Developed a task management API with FastAPI and Docker."],
                technologies=["FastAPI", "Docker"],
            )
        ],
        "skills": [
            ResumeSkillCategory(category_name="Languages", skills=["Python", "C / C++"]),
            ResumeSkillCategory(category_name="Tools", skills=["Docker", "Git / GitHub"]),
        ],
        "languages": [
            ResumeLanguage(language="English", proficiency="Advanced (C1)"),
            ResumeLanguage(language="Portuguese", proficiency="Native"),
        ],
        "certifications": ["AWS Cloud Practitioner"],
        "language": "en",
    }
    base.update(overrides)
    return TailoredResume(**base)  # type: ignore[arg-type]


def make_job(**overrides: object) -> JobPosting:
    """A job posting whose keywords partly overlap the synthetic candidate."""
    base: dict[str, object] = {
        "title": "Backend Software Intern",
        "company": "Globex",
        "raw_description": "Build backend services.",
        "technologies": ["Python", "FastAPI", "Kubernetes"],
        "keywords": ["REST API", "Teamwork"],
    }
    base.update(overrides)
    return JobPosting(**base)  # type: ignore[arg-type]
