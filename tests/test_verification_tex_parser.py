"""Tests for the LaTeX → TailoredResume parser, including a round trip through the real template."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
)
from src.generation.formatter import ResumeFormatter
from src.verification import parse_tex_resume
from src.verification.tex_parser import find_unschemed_links, split_top_level
from tests.verification_data import make_profile, make_resume

FIXTURES_DIR = Path(__file__).parent / "golden" / "fixtures"


@pytest.fixture
def formatter(tmp_path: Path) -> ResumeFormatter:
    return ResumeFormatter(output_dir=tmp_path)


def test_split_top_level_respects_parentheses() -> None:
    assert split_top_level("Python (Pandas, NumPy), SQL, C / C++") == ["Python (Pandas, NumPy)", "SQL", "C / C++"]
    assert split_top_level("a; b; (c; d)", ";") == ["a", "b", "(c; d)"]
    assert split_top_level("") == []
    assert split_top_level("English (Advanced (C1 - TOEIC)), French (Advanced)") == [
        "English (Advanced (C1 - TOEIC))", "French (Advanced)",
    ]


def test_find_unschemed_links() -> None:
    tex = r"\href{github.com/x}{G} \href{https://a.io}{A} \href{mailto:a@b.co}{m} \href{http://c.io}{C}"
    assert find_unschemed_links(tex) == ["github.com/x"]


def test_round_trip_through_the_real_template(formatter: ResumeFormatter) -> None:
    original = make_resume(
        objective_or_summary="Student focused on R&D with 100% passion; uses C# and C++.",
        experiences=[
            ResumeExperience(
                title="Backend Intern & Tester", organization="Acme_Corp & Sons", period="06/2023 - 09/2023",
                location="Paris, France",
                bullets=["Built REST APIs with 40% faster reports.", "Participated in code reviews."],
                technologies=["Python (Pandas, NumPy)", "PostgreSQL"],
            )
        ],
        projects=[
            ResumeProject(
                name="Task API", url="https://github.com/jane/task-api",
                bullets=["Developed a task API."], technologies=["FastAPI", "Docker"],
            ),
            ResumeProject(name="Notes", bullets=["Built notes."], technologies=["Flutter"]),
        ],
        skills=[ResumeSkillCategory(category_name="Programming & Tools", skills=["Python", "C / C++"])],
        languages=[
            ResumeLanguage(language="English", proficiency="Advanced (C1 - TOEIC)"),
            ResumeLanguage(language="Portuguese", proficiency="Native"),
        ],
        certifications=["AWS Cloud Practitioner", "Other (2024)"],
    )
    tex = formatter.render_latex(original)
    parsed = parse_tex_resume(tex)

    assert parsed.header == original.header
    assert parsed.target_job_title == original.target_job_title
    assert parsed.language == "en"
    assert parsed.objective_or_summary == original.objective_or_summary
    assert [(e.institution, e.degree, e.period, e.highlights) for e in parsed.education] == [
        (e.institution, e.degree, e.period, e.highlights) for e in original.education
    ]
    assert parsed.experiences == original.experiences
    assert parsed.projects == original.projects
    assert parsed.skills == original.skills
    assert parsed.languages == original.languages
    assert parsed.certifications == original.certifications


@pytest.mark.parametrize("language", ["pt", "fr"])
def test_round_trip_detects_localized_section_titles(formatter: ResumeFormatter, language: str) -> None:
    original = make_resume(language=language, certifications=[])
    parsed = parse_tex_resume(formatter.render_latex(original))
    assert parsed.language == language
    assert parsed.languages == original.languages
    assert parsed.certifications == []


def test_round_trip_omits_missing_optional_sections(formatter: ResumeFormatter) -> None:
    original = make_resume(
        objective_or_summary=None, education=[], projects=[], skills=[], languages=[], certifications=[],
    )
    parsed = parse_tex_resume(formatter.render_latex(original))
    assert parsed.objective_or_summary is None
    assert (parsed.education, parsed.projects, parsed.skills, parsed.languages, parsed.certifications) == ([], [], [], [], [])
    assert parsed.experiences == original.experiences


def test_round_trip_certifications_only_section(formatter: ResumeFormatter) -> None:
    original = make_resume(languages=[], certifications=["AWS Cloud Practitioner"])
    parsed = parse_tex_resume(formatter.render_latex(original))
    assert parsed.languages == [] and parsed.certifications == ["AWS Cloud Practitioner"]


def test_header_links_survive_and_empty_links_are_none(formatter: ResumeFormatter) -> None:
    header = make_resume().header.model_copy(update={"github_url": None, "portfolio_url": "https://jane.dev"})
    parsed = parse_tex_resume(formatter.render_latex(make_resume(header=header)))
    assert parsed.header.github_url is None
    assert parsed.header.portfolio_url == "https://jane.dev"
    assert parsed.header.linkedin_url == "https://linkedin.com/in/jane"


def test_parse_rejects_documents_not_made_with_the_template() -> None:
    with pytest.raises(ValueError):
        parse_tex_resume(r"\documentclass{article}\begin{document}Hello\end{document}")


def test_parse_rejects_unknown_section_titles(formatter: ResumeFormatter) -> None:
    tex = formatter.render_latex(make_resume()).replace("Work Experience", "My Wild Career")
    with pytest.raises(ValueError, match="unknown section title"):
        parse_tex_resume(tex)


@pytest.mark.parametrize("name", ["bad", "good"])
def test_golden_fixtures_parse(name: str) -> None:
    tex = (FIXTURES_DIR / f"{name}_amazon_resume.tex").read_text(encoding="utf-8")
    resume = parse_tex_resume(tex)
    assert resume.header.full_name == "Samuel Amadeu Loureiro"
    assert [e.organization for e in resume.experiences] == ["Asimov Jr.", "ENIB"]
    assert len(resume.projects) == 3 and len(resume.education) == 3
    assert [c.category_name for c in resume.skills] == [
        "Programming Languages", "Frameworks & Libraries", "Databases & Systems",
    ]
    assert [l.language for l in resume.languages] == ["Portuguese", "English", "French"]


def test_parser_keeps_raw_unschemed_urls_visible_to_the_url_check() -> None:
    tex = (FIXTURES_DIR / "bad_amazon_resume.tex").read_text(encoding="utf-8")
    assert find_unschemed_links(tex) == ["linkedin.com/in/samuelamadeuloureiro", "github.com/SamuelLoureiro"]
    assert parse_tex_resume(tex).header.linkedin_url.startswith("https://")  # model repairs it silently
