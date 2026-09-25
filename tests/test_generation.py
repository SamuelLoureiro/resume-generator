"""Unit and integration tests for generation prompts, LLM chain, and LaTeX PDF formatter."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock
import pytest

from src.data.candidate import (
    CandidateProfile,
    ContactInfo,
    Education,
    Experience,
    Language,
    Project,
    Skills,
)
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
from src.generation.chain import (
    ResumeGenerationChain,
    extract_json_payload,
    parse_tailored_resume,
)
from src.generation.formatter import (
    ResumeFormatter,
    sanitize_filename_part,
)
from src.generation.prompts import (
    SYSTEM_PROMPT,
    build_resume_generation_prompt,
    get_resume_schema_description,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_candidate() -> CandidateProfile:
    """Fixture providing a verified candidate profile."""
    return CandidateProfile(
        contact=ContactInfo(
            full_name="Lucas Rocha",
            email="lucas@example.com",
            phone="+55 11 98888-7777",
            location="São Paulo, SP - Brazil",
            linkedin_url="https://linkedin.com/in/lucasrocha",
            github_url="https://github.com/lucasrocha",
        ),
        summary="Computer Science undergraduate focused on ML and RAG systems.",
        education=[
            Education(
                institution="University of São Paulo",
                degree="Bachelor of Science in Computer Science",
                start_date="03/2023",
                end_date="12/2026",
                current=True,
                relevant_coursework=["Algorithms", "Artificial Intelligence", "Databases"],
                highlights=["Research Assistant in Natural Language Processing"],
            )
        ],
        experiences=[
            Experience(
                title="Undergraduate Research Assistant",
                organization="AI Lab USP",
                location="São Paulo, SP",
                start_date="08/2024",
                end_date="Present",
                current=True,
                bullets=[
                    "Engineered semantic retrieval pipelines using ChromaDB and Gemini embeddings.",
                    "Improved question-answering accuracy by 35% across 200 benchmark questions.",
                ],
                technologies=["Python", "LlamaIndex", "ChromaDB", "PyTorch"],
            )
        ],
        projects=[
            Project(
                name="RAG Resume Tailor",
                description="Generates tailored resumes matching job descriptions.",
                url="https://github.com/lucasrocha/rag-resume",
                bullets=[
                    "Built full RAG architecture using LlamaIndex and BM25 hybrid search.",
                    "Reduced resume preparation time by 80% while ensuring 100% factual accuracy.",
                ],
                technologies=["Python", "LlamaIndex", "FastAPI", "Docker"],
                highlight=True,
            )
        ],
        skills=Skills(
            programming_languages=["Python", "SQL", "C++"],
            frameworks_and_libraries=["LlamaIndex", "FastAPI", "PyTorch"],
            databases=["PostgreSQL", "ChromaDB"],
            tools_and_platforms=["Docker", "Git", "Linux"],
            soft_skills=["Team Collaboration", "Problem Solving"],
        ),
        languages=[
            Language(language="Portuguese", proficiency="Native"),
            Language(language="English", proficiency="Fluent (C1)"),
        ],
    )


@pytest.fixture
def sample_job() -> JobPosting:
    """Fixture providing an internship job posting."""
    return JobPosting(
        title="Machine Learning Engineering Intern",
        company="DeepMind Technologies",
        location="São Paulo, SP",
        work_model="Hybrid",
        raw_description="Looking for an intern to build RAG pipelines and evaluate LLMs.",
        requirements=["Strong Python skills", "Familiarity with vector databases"],
        desirables=["Experience with LlamaIndex or LangChain"],
        technologies=["Python", "LlamaIndex", "ChromaDB", "FastAPI"],
        keywords=["RAG", "LLM", "Embeddings"],
    )


@pytest.fixture
def sample_tailored_resume() -> TailoredResume:
    """Fixture providing a complete TailoredResume instance."""
    return TailoredResume(
        target_job_title="Machine Learning Engineering Intern",
        target_company="DeepMind Technologies",
        header=ResumeHeader(
            full_name="Lucas Rocha",
            email="lucas@example.com",
            phone="+55 11 98888-7777",
            location="São Paulo, SP - Brazil",
            linkedin_url="https://linkedin.com/in/lucasrocha",
            github_url="https://github.com/lucasrocha",
        ),
        objective_or_summary="Computer Science student passionate about building scalable RAG architectures.",
        education=[
            ResumeEducation(
                institution="University of São Paulo",
                degree="BSc in Computer Science",
                period="03/2023 - 12/2026",
                location="São Paulo, SP",
                highlights=["Research Scholar in NLP and Vector Search"],
            )
        ],
        experiences=[
            ResumeExperience(
                title="Research Assistant in AI",
                organization="AI Lab USP",
                period="08/2024 - Present",
                location="São Paulo, SP",
                bullets=[
                    "Engineered semantic retrieval pipelines using ChromaDB and Gemini embeddings.",
                    "Improved retrieval accuracy by 35% on standard benchmarks.",
                ],
                technologies=["Python", "LlamaIndex", "ChromaDB"],
            )
        ],
        projects=[
            ResumeProject(
                name="RAG Resume Tailor",
                technologies=["Python", "LlamaIndex", "FastAPI"],
                url="https://github.com/lucasrocha/rag-resume",
                bullets=["Built hybrid search pipeline with Reciprocal Rank Fusion."],
            )
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Languages & Frameworks",
                skills=["Python", "SQL", "FastAPI", "LlamaIndex"],
            )
        ],
        languages=[
            ResumeLanguage(language="English", proficiency="Fluent (C1)")
        ],
        certifications=["Deep Learning Specialization - DeepLearning.AI"],
    )


# ---------------------------------------------------------------------------
# Prompts tests
# ---------------------------------------------------------------------------

def test_system_prompt_mandates() -> None:
    """Test that SYSTEM_PROMPT contains all critical recruitment and anti-hallucination rules."""
    assert "ZERO HALLUCINATION" in SYSTEM_PROMPT
    assert "GOOGLE XYZ ACHIEVEMENT FORMULA" in SYSTEM_PROMPT
    assert "HIGH-IMPACT ACTION VERBS" in SYSTEM_PROMPT
    assert "TailoredResume" in SYSTEM_PROMPT


def test_get_resume_schema_description() -> None:
    """Test that schema description is valid JSON and contains required properties."""
    schema_str = get_resume_schema_description()
    schema_dict = json.loads(schema_str)

    assert "properties" in schema_dict
    assert "target_job_title" in schema_dict["properties"]
    assert "target_company" in schema_dict["properties"]
    assert "header" in schema_dict["properties"]


def test_build_resume_generation_prompt(
    sample_candidate: CandidateProfile,
    sample_job: JobPosting,
) -> None:
    """Test prompt building includes candidate info, job posting, and RAG guidelines."""
    guidelines = "### [Guideline 1: XYZ Formula]\nQuantify engineering results."
    prompt = build_resume_generation_prompt(
        candidate=sample_candidate,
        job=sample_job,
        retrieved_guidelines=guidelines,
    )

    assert "Lucas Rocha" in prompt
    assert "DeepMind Technologies" in prompt
    assert "Machine Learning Engineering Intern" in prompt
    assert "Guideline 1: XYZ Formula" in prompt
    assert "TailoredResume" in prompt


# ---------------------------------------------------------------------------
# Chain & Parsing tests
# ---------------------------------------------------------------------------

def test_extract_json_payload_direct() -> None:
    """Test extracting direct JSON string."""
    raw = '{"target_job_title": "Intern", "target_company": "Tech Corp"}'
    assert extract_json_payload(raw) == raw


def test_extract_json_payload_markdown_codeblock() -> None:
    """Test extracting JSON wrapped in markdown codeblock."""
    raw = """Here is the result:
```json
{
  "target_job_title": "Intern",
  "target_company": "Tech Corp"
}
```
Hope this helps!"""
    payload = extract_json_payload(raw)
    data = json.loads(payload)
    assert data["target_job_title"] == "Intern"


def test_extract_json_payload_invalid_raises() -> None:
    """Test that missing JSON braces raises ValueError."""
    with pytest.raises(ValueError, match="Could not extract JSON"):
        extract_json_payload("No json object here at all.")


def test_parse_tailored_resume_valid(sample_tailored_resume: TailoredResume) -> None:
    """Test parsing a valid JSON string into a TailoredResume instance."""
    json_text = sample_tailored_resume.model_dump_json()
    wrapped = f"```json\n{json_text}\n```"

    parsed = parse_tailored_resume(wrapped)
    assert parsed.target_job_title == sample_tailored_resume.target_job_title
    assert parsed.header.full_name == "Lucas Rocha"


def test_parse_tailored_resume_invalid_schema_raises() -> None:
    """Test that invalid payload structure raises ValueError."""
    invalid_json = '{"only_field": "invalid"}'
    with pytest.raises(ValueError, match="Invalid TailoredResume structure"):
        parse_tailored_resume(invalid_json)


def test_resume_generation_chain_with_mock_llm(
    sample_candidate: CandidateProfile,
    sample_job: JobPosting,
    sample_tailored_resume: TailoredResume,
) -> None:
    """Test ResumeGenerationChain executes chat and returns validated TailoredResume."""
    mock_llm = MagicMock()
    mock_response = MagicMock()
    mock_response.message.content = sample_tailored_resume.model_dump_json()
    mock_llm.chat.return_value = mock_response

    chain = ResumeGenerationChain(llm=mock_llm)
    result = chain.generate(
        candidate=sample_candidate,
        job=sample_job,
        retrieved_guidelines="Use strong action verbs.",
    )

    assert isinstance(result, TailoredResume)
    assert result.target_company == sample_tailored_resume.target_company
    mock_llm.chat.assert_called_once()


# ---------------------------------------------------------------------------
# Formatter & PDF tests
# ---------------------------------------------------------------------------

def test_sanitize_filename_part() -> None:
    """Test filename sanitization removes special chars and formats nicely."""
    assert sanitize_filename_part("Google DeepMind & Co.") == "google_deepmind_co"
    assert sanitize_filename_part(" Empresa 100% Tech ") == "empresa_100_tech"


def test_resume_formatter_render_latex(sample_tailored_resume: TailoredResume) -> None:
    """Test ResumeFormatter renders complete LaTeX source."""
    formatter = ResumeFormatter()
    latex = formatter.render_latex(sample_tailored_resume)

    assert r"\documentclass[10pt,a4paper]{article}" in latex
    assert "Lucas Rocha" in latex
    assert "Machine Learning Engineering Intern" in latex
    assert "AI Lab USP" in latex
    assert r"\begin{document}" in latex
    assert r"\end{document}" in latex


def test_resume_formatter_compile_pdf_with_tectonic(
    sample_tailored_resume: TailoredResume,
    tmp_path: Path,
) -> None:
    """Test full PDF compilation using Tectonic compiler."""
    formatter = ResumeFormatter(output_dir=tmp_path)
    pdf_path = formatter.compile_pdf(
        resume=sample_tailored_resume,
        output_filename="test_lucas_resume.pdf",
        keep_tex=True,
    )

    assert pdf_path.exists(), "Compiled PDF must exist"
    assert pdf_path.suffix == ".pdf"
    assert pdf_path.stat().st_size > 1000, "PDF file should have valid non-empty size"

    # Verify intermediate .tex was kept
    tex_path = tmp_path / "test_lucas_resume.tex"
    assert tex_path.exists()
