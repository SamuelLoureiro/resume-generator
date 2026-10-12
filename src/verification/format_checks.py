"""M5 — Format constraints (deterministic).

Checks whose input is missing (no PDF, no job title, no LaTeX source) are reported as
``not_verified`` instead of silently passing.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field

from src.data.resume import SECTION_LABELS, TailoredResume
from src.verification.tex_parser import find_unschemed_links
from src.verification.text_utils import tokenize

CheckStatus = Literal["pass", "fail", "not_verified"]

_PHONE_RE = re.compile(r"^\+\d{1,3}[\s\d().-]{6,}$")
# Country codes whose national numbers never start with a trunk "0" after the code.
_NO_TRUNK_ZERO_CODES = ("33", "44", "49", "55")

_LANGUAGE_MARKERS: dict[str, frozenset[str]] = {
    "en": frozenset({
        "the", "and", "of", "with", "for", "to", "in", "on", "by", "from", "using",
        "across", "an", "is", "are", "that", "via", "into", "while", "its", "their",
    }),
    "fr": frozenset({
        "le", "la", "les", "des", "du", "et", "avec", "pour", "dans", "sur", "par",
        "une", "un", "au", "aux", "en", "qui", "ainsi", "afin",
    }),
    "pt": frozenset({
        "o", "os", "e", "com", "para", "em", "uma", "um", "do", "da", "dos", "das",
        "na", "nas", "pelo", "pela", "por", "ao", "aos", "ou", "como",
    }),
}
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
_PROFILE_HOSTS = ("github.com", "gitlab.com", "bitbucket.org")


class FormatCheck(BaseModel):
    """Result of one format check.

    Attributes:
        name: Check identifier.
        status: ``pass``, ``fail`` or ``not_verified``.
        detail: Explanation, especially for failures.
    """

    model_config = ConfigDict(frozen=True)

    name: str
    status: CheckStatus
    detail: str = ""


class FormatResult(BaseModel):
    """Outcome of all M5 checks.

    Attributes:
        checks: Individual results.
    """

    model_config = ConfigDict(frozen=True)

    checks: list[FormatCheck] = Field(default_factory=list)

    @property
    def failed(self) -> list[FormatCheck]:
        """Checks with status ``fail``."""
        return [c for c in self.checks if c.status == "fail"]

    @property
    def not_verified(self) -> list[FormatCheck]:
        """Checks that could not run for lack of input."""
        return [c for c in self.checks if c.status == "not_verified"]

    @property
    def all_passed(self) -> bool:
        """True if no check failed (``not_verified`` checks do not count as failures)."""
        return not self.failed


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def count_pdf_pages(pdf_path: Path | str) -> int | None:
    """Return the page count of a PDF using ``pdfinfo``.

    Args:
        pdf_path: Path to a PDF file.

    Returns:
        int | None: Page count, or None if the file or ``pdfinfo`` is unavailable.
    """
    path = Path(pdf_path)
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None or not path.exists():
        return None
    proc = subprocess.run([pdfinfo, str(path)], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        return None
    for line in proc.stdout.splitlines():
        if line.startswith("Pages:"):
            return int(line.split(":", 1)[1].strip())
    return None


def check_one_page(pdf_path: Path | str | None) -> FormatCheck:
    """The compiled PDF must have exactly one page."""
    if pdf_path is None:
        return FormatCheck(name="one_page", status="not_verified", detail="no PDF supplied")
    pages = count_pdf_pages(pdf_path)
    if pages is None:
        return FormatCheck(
            name="one_page", status="not_verified", detail="PDF missing or pdfinfo unavailable"
        )
    if pages == 1:
        return FormatCheck(name="one_page", status="pass", detail="1 page")
    return FormatCheck(name="one_page", status="fail", detail=f"{pages} pages")


def check_no_empty_entries(resume: TailoredResume) -> FormatCheck:
    """No experience, project or skill category may be rendered without content."""
    empty: list[str] = []
    empty += [f"experience '{e.organization}'" for e in resume.experiences if not any(b.strip() for b in e.bullets)]
    empty += [f"project '{p.name}'" for p in resume.projects if not any(b.strip() for b in p.bullets)]
    empty += [f"skill category '{c.category_name}'" for c in resume.skills if not any(s.strip() for s in c.skills)]
    if resume.objective_or_summary is not None and not resume.objective_or_summary.strip():
        empty.append("summary")
    if empty:
        return FormatCheck(name="no_empty_entries", status="fail", detail="empty: " + "; ".join(empty))
    return FormatCheck(name="no_empty_entries", status="pass")


def check_section_titles(resume: TailoredResume, tex: str | None) -> FormatCheck:
    """The languages/certifications section title must match the content it holds."""
    if tex is None:
        return FormatCheck(name="section_titles", status="not_verified", detail="no LaTeX source supplied")
    combined = {labels["languages_certs"] for labels in SECTION_LABELS.values()}
    titles = [t.replace(r"\&", "&").strip() for t in re.findall(r"\\section\{([^}]*)\}", tex)]
    for title in titles:
        if title in combined and not (resume.languages and resume.certifications):
            return FormatCheck(
                name="section_titles",
                status="fail",
                detail=f"section titled '{title}' but languages or certifications are empty",
            )
    return FormatCheck(name="section_titles", status="pass")


def check_phone_format(phone: str) -> FormatCheck:
    """The phone must be in international format without a trunk zero (``+33 7 ...``)."""
    cleaned = (phone or "").strip()
    if not cleaned:
        return FormatCheck(name="phone_format", status="fail", detail="phone is empty")
    if not _PHONE_RE.match(cleaned):
        return FormatCheck(name="phone_format", status="fail", detail=f"'{cleaned}' is not international (+CC ...)")
    digits = re.sub(r"[^\d+]", "", cleaned)
    for code in _NO_TRUNK_ZERO_CODES:
        if digits.startswith(f"+{code}0"):
            return FormatCheck(
                name="phone_format", status="fail",
                detail=f"'{cleaned}' keeps the national trunk 0 after +{code}",
            )
    return FormatCheck(name="phone_format", status="pass")


def _valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and "." in parsed.netloc and " " not in url


def _is_bare_profile(url: str) -> bool:
    parsed = urlparse(url)
    host = parsed.netloc.lower().removeprefix("www.")
    segments = [s for s in parsed.path.split("/") if s]
    if host in _PROFILE_HOSTS:
        return len(segments) <= 1
    if host.endswith("linkedin.com"):
        return True
    return False


def check_urls(resume: TailoredResume, tex: str | None = None) -> FormatCheck:
    """Header links need an http(s) scheme; project links must not be bare profile pages.

    ``ResumeHeader`` prepends ``https://`` to scheme-less URLs, so scheme defects in a
    hand-written or archived document are only visible in the raw LaTeX (``tex``).
    """
    problems: list[str] = []
    if tex is not None:
        problems += [f"link without http(s) scheme in LaTeX: '{u}'" for u in find_unschemed_links(tex)]
    header = resume.header
    for label, url in (
        ("linkedin", header.linkedin_url),
        ("github", header.github_url),
        ("portfolio", header.portfolio_url),
    ):
        if url and url.strip() and not _valid_url(url):
            problems.append(f"header {label} URL invalid: '{url}'")
    for proj in resume.projects:
        if not (proj.url and proj.url.strip()):
            continue
        if not _valid_url(proj.url):
            problems.append(f"project '{proj.name}' URL invalid: '{proj.url}'")
        elif _is_bare_profile(proj.url):
            problems.append(f"project '{proj.name}' links to a bare profile page: '{proj.url}'")
    if problems:
        return FormatCheck(name="urls", status="fail", detail="; ".join(problems))
    return FormatCheck(name="urls", status="pass")


def detect_language(text: str) -> tuple[str | None, dict[str, int]]:
    """Guess the language of ``text`` from function-word hits.

    Args:
        text: A bullet or sentence.

    Returns:
        tuple[str | None, dict[str, int]]: Winning language code (None when there are
        fewer than 2 hits or a tie) and the hit counts per language.
    """
    words = [w.lower() for w in _WORD_RE.findall(text or "")]
    scores = {lang: sum(1 for w in words if w in markers) for lang, markers in _LANGUAGE_MARKERS.items()}
    ranked = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    top, runner_up = ranked[0], ranked[1]
    if top[1] < 2 or top[1] == runner_up[1]:
        return None, scores
    return top[0], scores


def check_single_language(resume: TailoredResume) -> FormatCheck:
    """Every sentence-like text must be in the resume's declared language."""
    texts: list[str] = []
    if resume.objective_or_summary:
        texts.append(resume.objective_or_summary)
    for exp in resume.experiences:
        texts.extend(exp.bullets)
    for proj in resume.projects:
        texts.extend(proj.bullets)
    for edu in resume.education:
        texts.extend(edu.highlights)
    mixed = []
    for text in texts:
        lang, _ = detect_language(text)
        if lang is not None and lang != resume.language:
            mixed.append(f"[{lang}] {text[:70]}")
    if mixed:
        return FormatCheck(
            name="single_language", status="fail",
            detail=f"resume language is '{resume.language}' but found: " + " | ".join(mixed),
        )
    return FormatCheck(name="single_language", status="pass")


def check_job_title_not_in_summary(resume: TailoredResume, job_title: str | None) -> FormatCheck:
    """The summary must not repeat the job title ("applying for the X role")."""
    title = (job_title if job_title is not None else resume.target_job_title) or ""
    summary_tokens = tokenize(resume.objective_or_summary or "")
    candidates = [title]
    candidates += [seg for seg in re.split(r"\s[-–—|]\s|,|\(", title)]
    for cand in list(candidates):
        tokens = tokenize(cand)
        while tokens and tokens[0].isdigit():  # "2027 Software Intern" -> "Software Intern"
            tokens = tokens[1:]
        if tokens != tokenize(cand):
            candidates.append(" ".join(tokens))
    for cand in candidates:
        cand_tokens = tokenize(cand)
        if len(cand_tokens) < 2:
            continue
        n = len(cand_tokens)
        if any(summary_tokens[i : i + n] == cand_tokens for i in range(len(summary_tokens) - n + 1)):
            return FormatCheck(
                name="job_title_not_in_summary", status="fail",
                detail=f"summary contains the job title '{cand.strip()}'",
            )
    if not tokenize(title):
        return FormatCheck(name="job_title_not_in_summary", status="not_verified", detail="no job title supplied")
    return FormatCheck(name="job_title_not_in_summary", status="pass")


def check_format(
    resume: TailoredResume,
    *,
    tex: str | None = None,
    pdf_path: Path | str | None = None,
    job_title: str | None = None,
) -> FormatResult:
    """Run every M5 check.

    Args:
        resume: Structured resume.
        tex: Rendered LaTeX source (enables the section-title check).
        pdf_path: Compiled PDF (enables the one-page check).
        job_title: Job title for the summary check; defaults to ``resume.target_job_title``.

    Returns:
        FormatResult: One :class:`FormatCheck` per constraint.
    """
    return FormatResult(
        checks=[
            check_one_page(pdf_path),
            check_no_empty_entries(resume),
            check_section_titles(resume, tex),
            check_phone_format(resume.header.phone),
            check_urls(resume, tex),
            check_single_language(resume),
            check_job_title_not_in_summary(resume, job_title),
        ]
    )
