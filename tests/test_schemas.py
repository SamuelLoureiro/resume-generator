"""Unit tests for Pydantic data schemas in src/data/."""

from pathlib import Path
import pytest
from pydantic import ValidationError

from src.data import (
    CandidateProfile,
    ContactInfo,
    Education,
    Experience,
    JobPosting,
    Language,
    Project,
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeProject,
    ResumeSkillCategory,
    Skills,
    TailoredResume,
    escape_latex,
)


def test_escape_latex() -> None:
    """Test that special LaTeX characters are properly escaped."""
    raw = "Skills: C++, R&D, 100% test, $500, #1, foo_bar, {brackets}, ~tilde, ^hat"
    escaped = escape_latex(raw)

    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\$" in escaped
    assert r"\#" in escaped
    assert r"\_" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped
    assert r"\textasciitilde{}" in escaped
    assert r"\textasciicircum{}" in escaped


def test_candidate_profile_validation() -> None:
    """Test validating and building CandidateProfile."""
    profile = CandidateProfile(
        contact=ContactInfo(
            full_name="John Smith",
            email="john@example.com",
            phone="+55 11 99999-9999",
            location="São Paulo, SP",
            linkedin_url="https://linkedin.com/in/johnsmith",
            github_url="https://github.com/johnsmith",
        ),
        summary="Computer Science student focused on AI.",
        education=[
            Education(
                institution="University of São Paulo",
                degree="Bachelor of Science in Computer Science",
                start_date="02/2023",
                end_date="12/2026",
                current=True,
                relevant_coursework=["Data Structures", "Artificial Intelligence"],
            )
        ],
        experiences=[
            Experience(
                title="Data Engineering Intern",
                organization="Tech Corp",
                start_date="01/2024",
                end_date="Present",
                current=True,
                bullets=["Built ETL pipelines with Python and SQL."],
                technologies=["Python", "SQL", "Docker"],
            )
        ],
        projects=[
            Project(
                name="RAG Assistant",
                description="Intelligent assistant with LlamaIndex and Gemini",
                bullets=["Achieved 92% semantic precision."],
                technologies=["Python", "LlamaIndex", "ChromaDB"],
                highlight=True,
            )
        ],
        skills=Skills(
            programming_languages=["Python", "SQL", "C++"],
            frameworks_and_libraries=["FastAPI", "PyTorch"],
            databases=["PostgreSQL", "ChromaDB"],
            tools_and_platforms=["Git", "Docker", "Linux"],
            soft_skills=["Communication", "Problem Solving"],
        ),
        languages=[
            Language(language="Portuguese", proficiency="Native"),
            Language(language="English", proficiency="Advanced (C1)"),
        ],
    )

    assert profile.contact.full_name == "John Smith"
    assert len(profile.education) == 1
    assert len(profile.experiences) == 1
    assert profile.skills.programming_languages[0] == "Python"


def test_candidate_profile_yaml_roundtrip(tmp_path: Path) -> None:
    """Test serializing to YAML and loading back to CandidateProfile."""
    profile = CandidateProfile(
        contact=ContactInfo(
            full_name="Maria Santos",
            email="maria@example.com",
            phone="(21) 98888-8888",
            location="Rio de Janeiro, RJ",
        ),
        education=[
            Education(
                institution="UFRJ",
                degree="Computer Engineering",
                start_date="2022",
                end_date="2026",
            )
        ],
    )

    yaml_file = tmp_path / "candidate_test.yaml"
    profile.to_yaml(yaml_file)

    assert yaml_file.exists()
    loaded_profile = CandidateProfile.from_yaml(yaml_file)

    assert loaded_profile.contact.full_name == "Maria Santos"
    assert loaded_profile.education[0].institution == "UFRJ"


def test_candidate_profile_missing_required_fields() -> None:
    """Test validation error when required contact fields are missing."""
    with pytest.raises(ValidationError):
        CandidateProfile(
            contact=ContactInfo(
                full_name="",  # invalid if we had min_length, but let's test missing email
            )  # type: ignore[call-arg]
        )


def test_job_posting_helpers() -> None:
    """Test search query generation and prompt formatting in JobPosting."""
    job = JobPosting(
        title="Machine Learning Engineering Intern",
        company="Startup AI",
        location="São Paulo, SP",
        work_model="Hybrid",
        raw_description="Looking for an intern to work with LLM and RAG models.",
        requirements=["Python proficiency", "Familiarity with Git and REST APIs"],
        desirables=["Prior experience with LangChain or LlamaIndex"],
        technologies=["Python", "FastAPI", "Docker", "ChromaDB"],
        keywords=["LLM", "RAG", "Prompt Engineering"],
    )

    query = job.to_search_query()
    assert "Startup AI" in query
    assert "Python" in query
    assert "Requirements:" in query

    prompt_context = job.to_prompt_context()
    assert "**Role:** Machine Learning Engineering Intern" in prompt_context
    assert "Mandatory Requirements:" in prompt_context
    assert "- Python proficiency" in prompt_context


def test_tailored_resume_latex_escaping() -> None:
    """Test that TailoredResume escapes all special LaTeX characters for rendering."""
    resume = TailoredResume(
        target_job_title="AI & Data Engineering Intern",
        target_company="Company 100% Tech",
        header=ResumeHeader(
            full_name="Carlos & Sons",
            email="carlos_dev@example.com",
            phone="11 99999-0000",
            location="São Paulo, SP",
        ),
        objective_or_summary="Focused on R&D for projects with 99% accuracy.",
        education=[
            ResumeEducation(
                institution="USP & Poli",
                degree="Software Engineering (Bachelor's)",
                period="03/2023 - 12/2026",
            )
        ],
        experiences=[
            ResumeExperience(
                title="R&D Research Intern",
                organization="Lab_AI",
                period="2024 - Present",
                bullets=["Improved performance by 40% using PyTorch & CUDA."],
                technologies=["Python", "C#", "SQL"],
            )
        ],
        projects=[
            ResumeProject(
                name="Project_X",
                technologies=["FastAPI & Docker"],
                bullets=["Built API with $0 infrastructure cost."],
            )
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Languages & Frameworks",
                skills=["Python", "C++", "C#"],
            )
        ],
    )

    context = resume.to_latex_context()

    assert r"\&" in context["target_job_title"]
    assert r"\%" in context["target_company"]
    assert r"\&" in context["header"]["full_name"]
    assert r"\_" in context["header"]["email"]
    assert r"\%" in context["objective_or_summary"]
    assert r"\&" in context["education"][0]["institution"]
    assert r"\_" in context["experiences"][0]["organization"]
    assert r"\$" in context["projects"][0]["bullets"][0]
    assert r"\#" in context["skills"][0]["skills"][2]


def test_default_candidate_profile_yaml_loads() -> None:
    """Test that the default candidate_profile.yaml loads and validates correctly."""
    default_yaml_path = Path("data/candidate_profile.yaml")
    assert default_yaml_path.exists(), "data/candidate_profile.yaml must exist"

    profile = CandidateProfile.from_yaml(default_yaml_path)
    assert profile.contact.full_name is not None
    assert len(profile.contact.full_name) > 0
    assert len(profile.education) > 0
    assert len(profile.experiences) > 0
    assert len(profile.projects) > 0
    assert len(profile.skills.programming_languages) > 0
    assert len(profile.languages) > 0
