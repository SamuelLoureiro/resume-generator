"""Unit tests for the M5 format checks (offline)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from src.data.resume import (
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
)
from src.verification import check_format
from src.verification import format_checks as fc
from tests.verification_data import make_resume


def _status(result, name: str) -> str:
    return next(c.status for c in result.checks if c.name == name)


# ---------------------------------------------------------------------------
# phone
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("phone", ["+33 7 43 52 84 87", "+55 11 98765-4321", "+44 20 7946 0958", "+1 415 555 0100"])
def test_phone_international_format_passes(phone: str) -> None:
    assert fc.check_phone_format(phone).status == "pass"


@pytest.mark.parametrize(
    "phone",
    ["+33 07 43 52 84 87", "+33 0743528487", "+55 (0)11 98765-4321", "0743528487", "07 43 52 84 87", "", "   ", "+33"],
)
def test_phone_invalid_format_fails(phone: str) -> None:
    assert fc.check_phone_format(phone).status == "fail"


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------

def test_urls_clean_resume_passes() -> None:
    assert fc.check_urls(make_resume()).status == "pass"


@pytest.mark.parametrize(
    "url",
    ["https://github.com/jane", "https://github.com/jane/", "https://www.linkedin.com/in/jane", "https://gitlab.com/jane"],
)
def test_project_link_to_bare_profile_fails(url: str) -> None:
    resume = make_resume(projects=[ResumeProject(name="Task API", url=url, bullets=["x"])])
    result = fc.check_urls(resume)
    assert result.status == "fail" and "bare profile" in result.detail


@pytest.mark.parametrize("url", ["https://github.com/jane/task-api", "https://lnkd.in/es9Zi695", "https://jane.dev/task-api"])
def test_project_link_to_repository_passes(url: str) -> None:
    resume = make_resume(projects=[ResumeProject(name="Task API", url=url, bullets=["x"])])
    assert fc.check_urls(resume).status == "pass"


def test_project_url_without_dot_in_host_is_invalid() -> None:
    resume = make_resume(projects=[ResumeProject(name="Task API", url="https://localhost/x", bullets=["x"])])
    assert fc.check_urls(resume).status == "fail"


def test_raw_latex_link_without_scheme_fails_even_though_the_model_repairs_it() -> None:
    tex = r"\href{linkedin.com/in/jane}{LinkedIn} \href{mailto:a@b.co}{a@b.co} \href{https://github.com/jane}{GitHub}"
    result = fc.check_urls(make_resume(), tex)
    assert result.status == "fail"
    assert "linkedin.com/in/jane" in result.detail
    assert "mailto" not in result.detail


# ---------------------------------------------------------------------------
# empty entries / section titles
# ---------------------------------------------------------------------------

def test_empty_entries_detected() -> None:
    resume = make_resume(
        experiences=[ResumeExperience(title="T", organization="O", period="2020", bullets=["", "  "])],
        projects=[ResumeProject(name="P", bullets=[])],
        skills=[ResumeSkillCategory(category_name="Tools", skills=[])],
    )
    result = fc.check_no_empty_entries(resume)
    assert result.status == "fail"
    for expected in ("experience 'O'", "project 'P'", "skill category 'Tools'"):
        assert expected in result.detail


def test_blank_summary_is_an_empty_section() -> None:
    assert fc.check_no_empty_entries(make_resume(objective_or_summary="  ")).status == "fail"
    assert fc.check_no_empty_entries(make_resume(objective_or_summary=None)).status == "pass"


def test_section_titles_not_verified_without_tex() -> None:
    assert fc.check_section_titles(make_resume(), None).status == "not_verified"


def test_combined_title_with_empty_certifications_fails() -> None:
    tex = "\\section{Languages \\& Certifications}\n"
    assert fc.check_section_titles(make_resume(certifications=[]), tex).status == "fail"
    assert fc.check_section_titles(make_resume(), tex).status == "pass"
    assert fc.check_section_titles(make_resume(certifications=[]), "\\section{Languages}\n").status == "pass"


def test_combined_title_in_french_and_portuguese_is_also_checked() -> None:
    for title in ("Langues \\& Certifications", "Idiomas \\& Certificações"):
        assert fc.check_section_titles(make_resume(certifications=[]), f"\\section{{{title}}}").status == "fail"


# ---------------------------------------------------------------------------
# single language
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("Developed a task management API with FastAPI and Docker for the team.", "en"),
        ("Développé une API de gestion de tâches avec FastAPI et Docker pour les équipes.", "fr"),
        ("Desenvolveu uma API de gerenciamento de tarefas com FastAPI e Docker para as equipes.", "pt"),
    ],
)
def test_detect_language(text: str, lang: str) -> None:
    assert fc.detect_language(text)[0] == lang


def test_detect_language_is_undecided_on_short_or_technical_text() -> None:
    assert fc.detect_language("Python, FastAPI, Docker")[0] is None
    assert fc.detect_language("")[0] is None


def test_single_language_passes_for_consistent_resume() -> None:
    assert fc.check_single_language(make_resume()).status == "pass"


def test_single_language_fails_when_a_bullet_is_in_another_language() -> None:
    resume = make_resume(
        projects=[
            ResumeProject(
                name="Task API",
                bullets=["Développé une API de gestion de tâches avec FastAPI pour les équipes de la société."],
            )
        ]
    )
    result = fc.check_single_language(resume)
    assert result.status == "fail" and "[fr]" in result.detail


def test_single_language_respects_declared_language() -> None:
    resume = make_resume(
        language="fr",
        objective_or_summary="Étudiant en informatique avec une expérience dans les services pour le web.",
        experiences=[], projects=[],
    )
    assert fc.check_single_language(resume).status == "pass"
    assert fc.check_single_language(resume.model_copy(update={"language": "en"})).status == "fail"


# ---------------------------------------------------------------------------
# job title in summary
# ---------------------------------------------------------------------------

def test_job_title_in_summary_fails() -> None:
    resume = make_resume(
        objective_or_summary="Student applying for the Backend Software Intern role at Globex.",
    )
    result = fc.check_job_title_not_in_summary(resume, "Backend Software Intern")
    assert result.status == "fail"


def test_job_title_with_location_suffix_is_caught_by_its_main_segment() -> None:
    resume = make_resume(objective_or_summary="Eager to join as a Software Dev Engineer Intern.")
    result = fc.check_job_title_not_in_summary(resume, "2027 Software Dev Engineer Intern - Luxembourg")
    assert result.status == "fail"


def test_job_title_check_ignores_case_and_punctuation() -> None:
    resume = make_resume(objective_or_summary="applying to the BACKEND, software-intern position")
    assert fc.check_job_title_not_in_summary(resume, "Backend Software Intern").status == "fail"


def test_job_title_absent_from_summary_passes() -> None:
    assert fc.check_job_title_not_in_summary(make_resume(), "Backend Software Intern").status == "pass"


def test_job_title_check_not_verified_without_title() -> None:
    resume = make_resume(target_job_title="")
    assert fc.check_job_title_not_in_summary(resume, None).status == "not_verified"


def test_job_title_check_defaults_to_the_resume_target_title() -> None:
    resume = make_resume(objective_or_summary="Seeking a Backend Software Intern position.")
    assert fc.check_job_title_not_in_summary(resume, None).status == "fail"


# ---------------------------------------------------------------------------
# page count
# ---------------------------------------------------------------------------

def test_one_page_not_verified_without_pdf() -> None:
    assert fc.check_one_page(None).status == "not_verified"
    assert fc.check_one_page("/nonexistent/file.pdf").status == "not_verified"


def _fake_pdfinfo(monkeypatch: pytest.MonkeyPatch, stdout: str, returncode: int = 0) -> None:
    monkeypatch.setattr(fc.shutil, "which", lambda name: "/usr/bin/pdfinfo")
    monkeypatch.setattr(
        fc.subprocess, "run",
        lambda *a, **k: subprocess.CompletedProcess(a, returncode, stdout=stdout, stderr=""),
    )


@pytest.mark.parametrize(("stdout", "status"), [("Title: x\nPages:          1\n", "pass"), ("Pages: 2\n", "fail")])
def test_one_page_uses_pdfinfo_output(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: str, status: str) -> None:
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _fake_pdfinfo(monkeypatch, stdout)
    assert fc.check_one_page(pdf).status == status


def test_one_page_not_verified_when_pdfinfo_fails_or_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pdf = tmp_path / "r.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    _fake_pdfinfo(monkeypatch, "", returncode=1)
    assert fc.check_one_page(pdf).status == "not_verified"
    monkeypatch.setattr(fc.shutil, "which", lambda name: None)
    assert fc.check_one_page(pdf).status == "not_verified"


def test_one_page_on_a_real_compiled_pdf(tmp_path: Path) -> None:
    tectonic = shutil.which("tectonic") or "/home/samuel/.local/bin/tectonic"
    if not Path(tectonic).exists() or shutil.which("pdfinfo") is None:
        pytest.skip("tectonic/pdfinfo not available")
    fixture = Path(__file__).parent / "golden" / "fixtures" / "good_amazon_resume.tex"
    proc = subprocess.run([tectonic, str(fixture), "--outdir", str(tmp_path)], capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr
    assert fc.check_one_page(tmp_path / "good_amazon_resume.pdf").status == "pass"


# ---------------------------------------------------------------------------
# check_format aggregate
# ---------------------------------------------------------------------------

def test_check_format_clean_resume_has_no_failures_and_lists_unverified() -> None:
    result = check_format(make_resume())
    assert result.all_passed
    assert {c.name for c in result.not_verified} == {"one_page", "section_titles"}


def test_check_format_reports_every_failure() -> None:
    resume = make_resume(
        header=ResumeHeader(full_name="Jane Doe", email="j@e.co", phone="+33 07 11 22 33 44", location="Paris"),
        languages=[ResumeLanguage(language="English", proficiency="Advanced (C1)")],
        certifications=[],
    )
    tex = "\\section{Languages \\& Certifications}\n"
    result = check_format(resume, tex=tex)
    assert {c.name for c in result.failed} == {"phone_format", "section_titles"}
    assert not result.all_passed
