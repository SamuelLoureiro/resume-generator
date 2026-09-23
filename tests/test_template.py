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
        target_job_title="Estágio em Engenharia de Machine Learning",
        target_company="Google DeepMind & Partners",
        header=ResumeHeader(
            full_name="Samuel Silva",
            email="samuel_dev@example.com",
            phone="+55 11 98765-4321",
            location="São Paulo, SP - Brasil",
            linkedin_url="https://linkedin.com/in/samuel",
            github_url="https://github.com/samuel",
            portfolio_url="https://samuel.dev",
        ),
        objective_or_summary=(
            "Estudante de Ciência da Computação buscando aplicar técnicas de RAG "
            "e modelos de LLM para aumentar a eficiência de processos em 30%."
        ),
        education=[
            ResumeEducation(
                institution="Universidade de São Paulo (USP)",
                degree="Bacharelado em Ciência da Computação",
                period="03/2023 - 12/2026",
                location="São Paulo, SP",
                highlights=[
                    "Bolsista de Iniciação Científica em NLP e RAG.",
                    "Monitor de Algoritmos e Estruturas de Dados.",
                ],
            )
        ],
        experiences=[
            ResumeExperience(
                title="Pesquisador de IC em Inteligência Artificial",
                organization="Lab_NLP & Computação",
                period="08/2024 - Presente",
                location="São Paulo, SP",
                bullets=[
                    "Implementou indexação semântica com ChromaDB e embeddings do Gemini.",
                    "Melhorou fidelidade das respostas em 45% com validação RAGAS.",
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
                    "Gerou currículos 100% personalizados e aderentes a ATS para vagas de estágio.",
                    "Reduziu tempo de criação manual de currículos em 90%.",
                ],
            )
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Linguagens & Frameworks",
                skills=["Python", "SQL", "C++", "FastAPI", "PyTorch"],
            ),
            ResumeSkillCategory(
                category_name="Bancos de Dados & Ferramentas",
                skills=["ChromaDB", "PostgreSQL", "Git", "Docker", "Linux"],
            ),
        ],
        languages=[
            ResumeLanguage(language="Português", proficiency="Nativo"),
            ResumeLanguage(language="Inglês", proficiency="Avançado (C1)"),
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
    assert "Universidade de São Paulo (USP)" in rendered_latex
    assert r"Lab\_NLP \& Computação" in rendered_latex
    assert "Resume\\_RAG\\_Generator" in rendered_latex or r"Resume\_RAG\_Generator" in rendered_latex

    # Assert special sections and escaped characters
    assert r"\&" in rendered_latex
    assert r"\%" in rendered_latex
    assert "Deep Learning Specialization - DeepLearning.AI" in rendered_latex
    assert "Inglês (Avançado (C1))" in rendered_latex
