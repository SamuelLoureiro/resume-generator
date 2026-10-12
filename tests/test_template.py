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


def test_template_multilingual_sections() -> None:
    """Test that templates/resume.tex.j2 renders localized section titles for PT, EN, and FR."""
    template_path = Path("templates/resume.tex.j2")
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
    template = env.from_string(template_path.read_text(encoding="utf-8"))
    resume = create_sample_tailored_resume()

    # 1. Portuguese
    resume.language = "pt"
    rendered_pt = template.render(**resume.to_latex_context())
    assert r"\section{Objetivo Profissional}" in rendered_pt
    assert r"\section{Formação Acadêmica}" in rendered_pt
    assert r"\section{Experiência Profissional}" in rendered_pt
    assert r"\section{Projetos em Destaque}" in rendered_pt
    assert r"\section{Habilidades Técnicas}" in rendered_pt
    assert r"\section{Idiomas \& Certificações}" in rendered_pt

    # 2. English
    resume.language = "en"
    rendered_en = template.render(**resume.to_latex_context())
    assert r"\section{Professional Summary}" in rendered_en
    assert r"\section{Education}" in rendered_en
    assert r"\section{Work Experience}" in rendered_en
    assert r"\section{Featured Projects}" in rendered_en
    assert r"\section{Technical Skills}" in rendered_en
    assert r"\section{Languages \& Certifications}" in rendered_en
    assert r"\textbf{Technologies:}" in rendered_en
    assert r"[View Project / Code]" in rendered_en

    # 3. French
    resume.language = "fr"
    rendered_fr = template.render(**resume.to_latex_context())
    assert r"\section{Profil Professionnel}" in rendered_fr
    assert r"\section{Formation}" in rendered_fr
    assert r"\section{Expérience Professionnelle}" in rendered_fr
    assert r"\section{Projets Notables}" in rendered_fr
    assert r"\section{Compétences Techniques}" in rendered_fr
    assert r"\section{Langues \& Certifications}" in rendered_fr
    assert r"\textbf{Technologies :}" in rendered_fr
    assert r"[Voir le projet / Dépôt]" in rendered_fr


def test_template_languages_certifications_conditional_headers() -> None:
    """Test TPL-01: Section header dynamically adjusts when either languages or certifications is empty."""
    template_path = Path("templates/resume.tex.j2")
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
    template = env.from_string(template_path.read_text(encoding="utf-8"))

    # Case 1: Languages present, Certifications empty (EN)
    resume_en = create_sample_tailored_resume()
    resume_en.language = "en"
    resume_en.certifications = []
    rendered = template.render(**resume_en.to_latex_context())
    assert r"\section{Languages}" in rendered
    assert r"\section{Languages \& Certifications}" not in rendered
    assert r"\section{Certifications}" not in rendered

    # Case 2: Languages present, Certifications empty (PT)
    resume_pt = create_sample_tailored_resume()
    resume_pt.language = "pt"
    resume_pt.certifications = []
    rendered = template.render(**resume_pt.to_latex_context())
    assert r"\section{Idiomas}" in rendered
    assert r"\section{Idiomas \& Certificações}" not in rendered
    assert r"\section{Certificações}" not in rendered

    # Case 3: Certifications present, Languages empty (EN)
    resume_certs = create_sample_tailored_resume()
    resume_certs.language = "en"
    resume_certs.languages = []
    rendered = template.render(**resume_certs.to_latex_context())
    assert r"\section{Certifications}" in rendered
    assert r"\section{Languages \& Certifications}" not in rendered
    assert r"\section{Languages}" not in rendered
