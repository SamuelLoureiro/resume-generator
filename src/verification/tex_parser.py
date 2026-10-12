"""Parse a LaTeX resume rendered by the project template back into a ``TailoredResume``.

This exists so the deterministic checks can also be run on resumes that exist only as
``.tex`` (the archived Amazon resume, hand-corrected resumes used to validate the judge
in phase P6). It understands **only** the structure produced by
``templates/resume.tex.j2``; anything else raises ``ValueError`` rather than guessing.
"""

from __future__ import annotations

import re

from src.data.resume import (
    SECTION_LABELS,
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.verification.text_utils import unescape_latex

_SECTION_RE = re.compile(r"\\section\{([^}]*)\}")
_ENTRY_RE = re.compile(
    r"\\noindent\s*\\textbf\{\\color\{primary\}\s*(?P<title>.*?)\}(?P<rest>.*?)"
    r"(?=\\noindent\s*\\textbf\{\\color\{primary\}|\Z)",
    re.DOTALL,
)
_HFILL_RE = re.compile(r"\\hfill\s*\{\\small\\color\{subtext\}\s*(?P<period>.*?)\}")
_LOCATION_RE = re.compile(r"\\newline\s*\{\\footnotesize\\color\{subtext\}\s*(?P<loc>.*?)\}")
_TECH_RE = re.compile(r"\\newline\s*\{\\footnotesize\\textbf\{[^}]*\}\s*\\textit\{(?P<tech>.*?)\}\}")
_PROJECT_URL_RE = re.compile(r"\\hfill\s*\{\\footnotesize\\href\{(?P<url>[^}]*)\}")
_ITEM_RE = re.compile(r"\\item\s*\\small\s*(?P<text>.+)")
_SKILL_RE = re.compile(r"\\noindent\\textbf\{(?P<cat>[^}]*?):?\}\s*(?P<skills>.*?)\\\\\[1\.5pt\]", re.DOTALL)
_HREF_RE = re.compile(r"\\href\{(?P<url>[^}]*)\}\{(?P<label>[^}]*)\}")


def _build_section_keys() -> dict[str, tuple[str, str]]:
    """Map every unescaped section title to (section key, language code)."""
    mapping: dict[str, tuple[str, str]] = {}
    for lang, labels in SECTION_LABELS.items():
        for key in ("objective", "education", "experience", "projects", "skills"):
            mapping[labels[key]] = (key, lang)
        for key in ("languages_certs", "languages_only", "certifications_only"):
            mapping[labels[key]] = ("langs", lang)
    return mapping


_SECTION_KEYS = _build_section_keys()


def split_top_level(text: str, separator: str = ",") -> list[str]:
    """Split ``text`` on ``separator`` outside parentheses.

    Args:
        text: Text such as ``"Python (Pandas, NumPy), SQL"``.
        separator: Single-character separator.

    Returns:
        list[str]: Stripped non-empty parts.
    """
    parts: list[str] = []
    depth = 0
    current: list[str] = []
    for ch in text:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        if ch == separator and depth == 0:
            parts.append("".join(current))
            current = []
        else:
            current.append(ch)
    parts.append("".join(current))
    return [p.strip() for p in parts if p.strip()]


def find_unschemed_links(tex: str) -> list[str]:
    """Return ``\\href`` targets (other than ``mailto:``) lacking an http(s) scheme.

    ``ResumeHeader``/``ResumeProject`` silently prepend ``https://`` when parsing, so the
    defect is only visible in the raw LaTeX.

    Args:
        tex: LaTeX source.

    Returns:
        list[str]: Offending URLs as written.
    """
    return [
        m.group("url")
        for m in _HREF_RE.finditer(tex)
        if not m.group("url").startswith(("http://", "https://", "mailto:"))
    ]


def _strip_comments(tex: str) -> str:
    return re.sub(r"(?<!\\)%.*", "", tex)


def _parse_header(tex: str) -> ResumeHeader:
    name_match = re.search(r"\\Huge\\bfseries\\color\{primary\}\s*(?P<name>.*?)\}\\\\", tex)
    block_match = re.search(r"\\small\\color\{subtext\}(?P<block>.*?)\\end\{center\}", tex, re.DOTALL)
    if not name_match or not block_match:
        raise ValueError("Unsupported LaTeX: header block not found")
    block = block_match.group("block")
    segments = [s.strip() for s in re.split(r"\\quad\|\\quad", block)]
    location = unescape_latex(segments[0]) if segments else ""
    phone = unescape_latex(segments[1]) if len(segments) > 1 else ""
    email = ""
    links: dict[str, str] = {}
    for m in _HREF_RE.finditer(block):
        if m.group("url").startswith("mailto:"):
            email = m.group("url")[len("mailto:"):]
        else:
            links[m.group("label").lower()] = m.group("url")
    return ResumeHeader(
        full_name=unescape_latex(name_match.group("name")),
        email=email,
        phone=phone,
        location=location,
        linkedin_url=links.get("linkedin"),
        github_url=links.get("github"),
        portfolio_url=links.get("portfolio"),
    )


def _items(rest: str) -> list[str]:
    return [unescape_latex(m.group("text")) for m in _ITEM_RE.finditer(rest)]


def _technologies(rest: str) -> list[str]:
    m = _TECH_RE.search(rest)
    return [unescape_latex(t) for t in split_top_level(m.group("tech"))] if m else []


def _parse_education(body: str) -> list[ResumeEducation]:
    entries: list[ResumeEducation] = []
    for m in _ENTRY_RE.finditer(body):
        rest = m.group("rest")
        head = re.match(r"\s*,\s*(?P<inst>.*?)\s*\\hfill", rest, re.DOTALL)
        period = _HFILL_RE.search(rest)
        loc = _LOCATION_RE.search(rest)
        raw_period = unescape_latex(period.group("period")) if period else ""
        norm_period = re.sub(r"\s*(?:[–—]|--|-)\s*", " - ", raw_period).strip()
        entries.append(
            ResumeEducation(
                institution=unescape_latex(head.group("inst")) if head else "",
                degree=unescape_latex(m.group("title")),
                period=norm_period,
                location=unescape_latex(loc.group("loc")) if loc else None,
                highlights=_items(rest),
            )
        )
    return entries


def _parse_experiences(body: str) -> list[ResumeExperience]:
    entries: list[ResumeExperience] = []
    for m in _ENTRY_RE.finditer(body):
        rest = m.group("rest")
        head = re.match(r"\s*,\s*(?P<org>.*?)\s*\\hfill", rest, re.DOTALL)
        period = _HFILL_RE.search(rest)
        loc = _LOCATION_RE.search(rest)
        raw_period = unescape_latex(period.group("period")) if period else ""
        norm_period = re.sub(r"\s*(?:[–—]|--|-)\s*", " - ", raw_period).strip()
        entries.append(
            ResumeExperience(
                title=unescape_latex(m.group("title")),
                organization=unescape_latex(head.group("org")) if head else "",
                period=norm_period,
                location=unescape_latex(loc.group("loc")) if loc else None,
                bullets=_items(rest),
                technologies=_technologies(rest),
            )
        )
    return entries


def _parse_projects(body: str) -> list[ResumeProject]:
    entries: list[ResumeProject] = []
    for m in _ENTRY_RE.finditer(body):
        rest = m.group("rest")
        url = _PROJECT_URL_RE.search(rest)
        entries.append(
            ResumeProject(
                name=unescape_latex(m.group("title")),
                url=url.group("url") if url else None,
                bullets=_items(rest),
                technologies=_technologies(rest),
            )
        )
    return entries


def _parse_skills(body: str) -> list[ResumeSkillCategory]:
    return [
        ResumeSkillCategory(
            category_name=unescape_latex(m.group("cat")),
            skills=[unescape_latex(s) for s in split_top_level(m.group("skills"))],
        )
        for m in _SKILL_RE.finditer(body)
    ]


def _parse_languages_and_certs(body: str, lang: str) -> tuple[list[ResumeLanguage], list[str]]:
    labels = SECTION_LABELS[lang]
    lang_label = labels["languages"].rstrip(": ").strip()
    cert_label = labels["certifications"].rstrip(": ").strip()
    languages: list[ResumeLanguage] = []
    certs: list[str] = []
    chunks = re.split(r"\\\\\[1\.5pt\]", body)
    for chunk in chunks:
        m = re.search(r"\\noindent(?:\\textbf\{(?P<label>[^}]*)\})?\s*(?P<text>.*)", chunk, re.DOTALL)
        if not m:
            continue
        raw_label = m.group("label")
        label = raw_label.rstrip(": ").strip() if raw_label else ""
        text = re.sub(r"\s+", " ", m.group("text")).strip()
        if not text:
            continue
        if label == lang_label or not label:
            for item in split_top_level(text):
                name, _, rest = item.partition(" (")
                proficiency = rest[:-1] if rest.endswith(")") else rest
                languages.append(
                    ResumeLanguage(
                        language=unescape_latex(name), proficiency=unescape_latex(proficiency)
                    )
                )
        elif label == cert_label:
            certs.extend(unescape_latex(c) for c in split_top_level(text, ";"))
    return languages, certs


def parse_tex_resume(tex: str) -> TailoredResume:
    """Parse template-rendered LaTeX into a structured resume.

    Args:
        tex: LaTeX source produced by ``templates/resume.tex.j2``.

    Returns:
        TailoredResume: Parsed resume. ``target_company`` is empty (the template does not
        render it); ``target_job_title`` is read from the ``pdftitle`` metadata.

    Raises:
        ValueError: If the document does not follow the project template.
    """
    source = _strip_comments(tex)
    header = _parse_header(source)

    title_match = re.search(r"pdftitle=\{Curriculum - (?P<name>.*?) - (?P<title>.*?)\}\s*\}", source, re.DOTALL)
    job_title = unescape_latex(title_match.group("title")) if title_match else ""

    sections = list(_SECTION_RE.finditer(source))
    if not sections:
        raise ValueError("Unsupported LaTeX: no \\section found")

    data: dict[str, object] = {}
    language_code = "en"
    langs_body = ""
    langs_lang = None
    for idx, sec in enumerate(sections):
        end = sections[idx + 1].start() if idx + 1 < len(sections) else source.find("\\end{document}")
        body = source[sec.end(): end if end != -1 else len(source)]
        title = unescape_latex(sec.group(1))
        found = _SECTION_KEYS.get(title)
        if found is None:
            raise ValueError(f"Unsupported LaTeX: unknown section title '{title}'")
        key, lang = found
        if key != "langs":
            language_code = lang
        if key == "objective":
            data["objective_or_summary"] = unescape_latex(re.sub(r"\\small\\color\{primary\}", "", body))
        elif key == "education":
            data["education"] = _parse_education(body)
        elif key == "experience":
            data["experiences"] = _parse_experiences(body)
        elif key == "projects":
            data["projects"] = _parse_projects(body)
        elif key == "skills":
            data["skills"] = _parse_skills(body)
        else:
            langs_body, langs_lang = body, lang

    languages: list[ResumeLanguage] = []
    certs: list[str] = []
    if langs_body:
        languages, certs = _parse_languages_and_certs(langs_body, langs_lang or language_code)

    return TailoredResume(
        target_job_title=job_title,
        target_company="",
        header=header,
        languages=languages,
        certifications=certs,
        language=language_code,  # type: ignore[arg-type]
        **data,  # type: ignore[arg-type]
    )
