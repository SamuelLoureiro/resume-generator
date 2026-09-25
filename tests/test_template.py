"""Unit tests for LaTeX Jinja2 template rendering."""

from pathlib import Path
import jinja2

from src.data import (
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)


def create_sample_tailored_resume() -> TailoredResume:
    """Helper to generate a rich TailoredResume fixture."""
    return TailoredResume(
        target_job_title="Machine Learning Engineering Intern",
        target_company="Google DeepMind & Partners",
        header=ResumeHeader(
            full_name="Samuel Silva",
            email="samuel_dev@example.com",
            phone="+55 11 98765-4321",
            location="São Paulo, SP - Brazil",
            linkedin_url="https://linkedin.com/in/samuel",
            github_url="https://github.com/samuel",
            portfolio_url="https://samuel.dev",
        ),
        objective_or_summary=(
            "Computer Science student seeking to apply RAG techniques "
            "and LLM models to improve process efficiency by 30%."
        ),
        education=[
            ResumeEducation(
                institution="University of São Paulo (USP)",
                degree="Bachelor of Science in Computer Science",
                period="03/2023 - 12/2026",
                location="São Paulo, SP",
                highlights=[
                    "Undergraduate Research Scholar in NLP and RAG.",
                    "Teaching Assistant for Algorithms and Data Structures.",
                ],
            )
        ],
        experiences=[
            ResumeExperience(
                title="Undergraduate Research Assistant in Artificial Intelligence",
                organization="Lab_NLP & Computing",
                period="08/2024 - Present",
                location="São Paulo, SP",
                bullets=[
                    "Implemented semantic indexing with ChromaDB and Gemini embeddings.",
                    "Improved response fidelity by 45% using RAGAS evaluation.",
                ],
                technologies=["Python", "LlamaIndex", "ChromaDB", "Docker"],
            )
        ],
        projects=[
            ResumeProject(
                name="Resume_RAG_Generator",
                technologies=["Python", "Gemini 2.5", "Gradio", "LaTeX"],
                url="https://github.com/samuel/gerador-curriculos",
                bullets=[
                    "Generated 100% personalized, ATS-compliant resumes for internship applications.",
                    "Reduced manual resume creation time by 90%.",
                ],
            )
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Languages & Frameworks",
                skills=["Python", "SQL", "C++", "FastAPI", "PyTorch"],
            ),
            ResumeSkillCategory(
                category_name="Databases & Tools",
                skills=["ChromaDB", "PostgreSQL", "Git", "Docker", "Linux"],
            ),
        ],
        languages=[
            ResumeLanguage(language="Portuguese", proficiency="Native"),
            ResumeLanguage(language="English", proficiency="Advanced (C1)"),
        ],
        certifications=[
            "Deep Learning Specialization - DeepLearning.AI",
            "Machine Learning with Python - IBM",
        ],
    )


def test_resume_template_rendering() -> None:
    """Test rendering templates/resume.tex.j2 with Jinja2 using custom delimiters."""
    template_path = Path("templates/resume.tex.j2")
    assert template_path.exists(), "Template file must exist"

    env = jinja2.Environment(
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )

    with open(template_path, "r", encoding="utf-8") as f:
        template_content = f.read()

    template = env.from_string(template_content)

    resume = create_sample_tailored_resume()
    context = resume.to_latex_context()

    rendered_latex = template.render(**context)

    # Assert basic LaTeX document structure
    assert r"\documentclass[10pt,a4paper]{article}" in rendered_latex
    assert r"\begin{document}" in rendered_latex
    assert r"\end{document}" in rendered_latex

    # Assert candidate info was injected
    assert "Samuel Silva" in rendered_latex
    assert r"samuel\_dev@example.com" in rendered_latex
    assert "University of São Paulo (USP)" in rendered_latex
    assert r"Lab\_NLP \& Computing" in rendered_latex
    assert "Resume\\_RAG\\_Generator" in rendered_latex or r"Resume\_RAG\_Generator" in rendered_latex

    # Assert special sections and escaped characters
    assert r"\&" in rendered_latex
    assert r"\%" in rendered_latex
    assert "Deep Learning Specialization - DeepLearning.AI" in rendered_latex
    assert "English (Advanced (C1))" in rendered_latex
