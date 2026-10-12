"""M1 (a–c) — deterministic fabrication checks.

(a) skills / technologies must be on the profile allowlist;
(b) numbers must appear in the profile or the verified facts;
(c) organizations, titles, degrees, institutions, periods, project names/URLs,
    certifications and spoken languages must match the profile.

Free-text claims that none of these rules can judge (e.g. "distributed systems" in a
bullet) are *not* decided here: they are the job of the claim-level judge (M1d, P6).
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.data.resume import TailoredResume
from src.verification.ground_truth import GroundTruth, extract_numbers
from src.verification.text_utils import STOPWORDS, tokenize

SubMetric = Literal["a", "b", "c"]

_DATE_RE = re.compile(r"(\d{1,2})/(\d{4})|(?<!\d)(\d{4})(?!\d)")
_PRESENT_WORDS = {"present", "presente", "présent", "atual", "atualmente", "current", "now", "aujourd'hui"}
_COURSEWORK_LABEL_RE = re.compile(
    r"^\s*(relevant\s+coursework|coursework|disciplinas?\s+relevantes?|cours\s+pertinents?)\s*:\s*(.+)$",
    re.IGNORECASE,
)

_LANGUAGE_ALIASES: dict[str, str] = {
    "português": "portuguese", "portugues": "portuguese", "portugais": "portuguese",
    "inglês": "english", "ingles": "english", "anglais": "english",
    "francês": "french", "frances": "french", "français": "french", "francais": "french",
    "espanhol": "spanish", "espagnol": "spanish", "español": "spanish", "espanol": "spanish",
}
_PROFICIENCY_CLASSES: tuple[frozenset[str], ...] = (
    frozenset({"native", "nativo", "natif", "maternelle", "mother", "bilingual"}),
    frozenset({"advanced", "avançado", "avancado", "avancé", "avance", "fluent", "fluente", "courant"}),
    frozenset({"intermediate", "intermediário", "intermediario", "intermédiaire", "intermediaire"}),
    frozenset({"basic", "básico", "basico", "elementary", "débutant", "debutant", "beginner"}),
)
_CEFR_RE = re.compile(r"\b([abc][12])\b", re.IGNORECASE)


class UnsupportedClaim(BaseModel):
    """A resume claim that the ground truth does not support.

    Attributes:
        sub: Sub-metric: ``a`` skills, ``b`` numbers, ``c`` entities/dates.
        kind: Claim kind (``skill``, ``number``, ``organization``, ``title``, ...).
        text: The claim as written in the resume.
        reason: Why it is unsupported.
    """

    model_config = ConfigDict(frozen=True)

    sub: SubMetric
    kind: str
    text: str
    reason: str


class FabricationResult(BaseModel):
    """Outcome of the deterministic fabrication checks (M1a–c).

    Attributes:
        checked: Number of claims checked per sub-metric.
        unsupported: Unsupported claims found.
    """

    model_config = ConfigDict(frozen=True)

    checked: dict[str, int] = Field(default_factory=lambda: {"a": 0, "b": 0, "c": 0})
    unsupported: list[UnsupportedClaim] = Field(default_factory=list)

    @property
    def total_claims(self) -> int:
        """Total number of claims checked across a, b and c."""
        return sum(self.checked.values())

    @property
    def rate(self) -> float | None:
        """Unsupported ÷ checked claims; None if nothing was checked."""
        if self.total_claims == 0:
            return None
        return len(self.unsupported) / self.total_claims

    def unsupported_of(self, sub: SubMetric) -> list[UnsupportedClaim]:
        """Return the unsupported claims of one sub-metric."""
        return [c for c in self.unsupported if c.sub == sub]


class _Collector:
    """Accumulates checked / unsupported counts while the checks run."""

    def __init__(self) -> None:
        self.checked: dict[str, int] = {"a": 0, "b": 0, "c": 0}
        self.unsupported: list[UnsupportedClaim] = []

    def check(self, sub: SubMetric, kind: str, text: str, ok: bool, reason: str) -> None:
        self.checked[sub] += 1
        if not ok:
            self.unsupported.append(UnsupportedClaim(sub=sub, kind=kind, text=text, reason=reason))

    def result(self) -> FabricationResult:
        return FabricationResult(checked=self.checked, unsupported=self.unsupported)


# ---------------------------------------------------------------------------
# Name / date helpers
# ---------------------------------------------------------------------------

_MULTILINGUAL_SYNONYMS: dict[str, str] = {
    "informatique": "computer",
    "computação": "computer",
    "computacao": "computer",
    "chercheur": "researcher",
    "pesquisador": "researcher",
    "développement": "development",
    "developpement": "development",
    "desenvolvimento": "development",
    "embarqués": "embedded",
    "embarques": "embedded",
    "embarcados": "embedded",
    "systèmes": "systems",
    "systemes": "systems",
    "sistemas": "systems",
    "interactifs": "interactive",
    "interactif": "interactive",
    "interativo": "interactive",
    "interativos": "interactive",
    "intelligents": "intelligent",
    "intelligent": "intelligent",
    "inteligente": "intelligent",
    "inteligentes": "intelligent",
    "autonomes": "autonomous",
    "autonome": "autonomous",
    "autônomos": "autonomous",
    "autonomos": "autonomous",
    "responsable": "manager",
    "gerente": "manager",
    "gestionnaire": "manager",
    "ingénieur": "engineering",
    "ingenieur": "engineering",
    "engenharia": "engineering",
    "ingénierie": "engineering",
    "ingenierie": "engineering",
    "diplôme": "degree",
    "diplome": "degree",
    "bureau": "board",
    "présidence": "presidency",
    "presidence": "presidency",
    "président": "officer",
    "membre": "member",
    "membro": "member",
    "apprentissage": "learning",
    "virtuelle": "virtual",
    "virtuel": "virtual",
}


def _name_tokens(text: str) -> set[str]:
    raw_tokens = {t for t in tokenize(text) if t not in STOPWORDS}
    return {_MULTILINGUAL_SYNONYMS.get(t, t) for t in raw_tokens}


def names_match(a: str, b: str) -> bool:
    """Return True if one name's tokens are contained in the other's.

    Tolerates rewordings such as ``"SPE UNIFEI"`` vs
    ``"SPE (Society of Petroleum Engineers) UNIFEI"`` as well as multilingual
    translations between French/Portuguese and English. Empty names never match.
    """
    ta, tb = _name_tokens(a), _name_tokens(b)
    if not ta or not tb:
        return False
    return ta <= tb or tb <= ta


def normalize_date(token: str) -> str:
    """Normalize ``9/2025`` to ``09/2025``; leave years and other strings untouched."""
    match = re.fullmatch(r"(\d{1,2})/(\d{4})", token.strip())
    if match:
        return f"{int(match.group(1)):02d}/{match.group(2)}"
    return token.strip()


def parse_period(period: str) -> tuple[str | None, str | None]:
    """Parse ``"09/2025 - 12/2025"`` or ``"2023 - Present"`` into (start, end).

    Args:
        period: Period string as written in the resume.

    Returns:
        tuple[str | None, str | None]: Normalized start and end; end is ``"present"``
        for open-ended periods; either may be None if not found.
    """
    dates = [normalize_date(m.group(0)) for m in _DATE_RE.finditer(period or "")]
    lowered = (period or "").lower()
    has_present = any(word in lowered for word in _PRESENT_WORDS)
    start = dates[0] if dates else None
    if len(dates) >= 2:
        end: str | None = dates[1]
    elif has_present:
        end = "present"
    else:
        end = None
    return start, end


def _date_matches(resume_date: str | None, profile_date: str) -> bool:
    if resume_date is None:
        return False
    pdate = normalize_date(profile_date)
    if resume_date == pdate:
        return True
    if re.fullmatch(r"\d{4}", resume_date):  # year-only is accepted if the year matches
        return pdate.endswith(resume_date)
    return False


def period_matches(period: str, start_date: str, end_date: str, current: bool) -> bool:
    """Return True if a resume period agrees with a profile entry's dates."""
    start, end = parse_period(period)
    if not _date_matches(start, start_date):
        return False
    if end == "present":
        return current
    return _date_matches(end, end_date)


def _normalize_url(url: str) -> str:
    cleaned = re.sub(r"^https?://", "", (url or "").strip().lower())
    cleaned = re.sub(r"^www\.", "", cleaned)
    return cleaned.rstrip("/")


def _proficiency_matches(resume_level: str, profile_level: str) -> bool:
    ra, pa = _name_tokens(resume_level), _name_tokens(profile_level)
    if ra and pa and (ra <= pa or pa <= ra):
        return True
    r_cefr = {m.lower() for m in _CEFR_RE.findall(resume_level)}
    p_cefr = {m.lower() for m in _CEFR_RE.findall(profile_level)}
    if r_cefr:
        return bool(r_cefr & p_cefr)
    lowered_r = {w.lower() for w in re.findall(r"[\wçãéêíóúâ']+", resume_level)}
    lowered_p = {w.lower() for w in re.findall(r"[\wçãéêíóúâ']+", profile_level)}
    return any(cls & lowered_r and cls & lowered_p for cls in _PROFICIENCY_CLASSES)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def check_fabrication(
    resume: TailoredResume,
    truth: GroundTruth,
    extra_allowed_numbers: set[str] | None = None,
) -> FabricationResult:
    """Run M1a, M1b and M1c on a resume.

    Header contact fields are not checked: they are injected from the profile at render
    time (phase P2). Only the candidate name is compared.

    Args:
        resume: Structured resume.
        truth: Ground-truth lookups built from the profile and facts.
        extra_allowed_numbers: Numbers allowed besides profile/facts (e.g. digits in the
            job title, which a summary may legitimately repeat).

    Returns:
        FabricationResult: Counts and the list of unsupported claims.
    """
    col = _Collector()
    profile = truth.profile

    # --- (a) skills & technologies --------------------------------------------
    skill_items: list[tuple[str, str]] = []
    for cat in resume.skills:
        skill_items.extend((item, f"skills/{cat.category_name}") for item in cat.skills)
    for exp in resume.experiences:
        skill_items.extend((item, f"technologies/{exp.organization}") for item in exp.technologies)
    for proj in resume.projects:
        skill_items.extend((item, f"technologies/{proj.name}") for item in proj.technologies)
    for item, where in skill_items:
        col.check(
            "a", "skill", item, truth.is_allowed_skill(item),
            f"'{item}' ({where}) is not in the profile skills, technologies or fact tags",
        )

    # --- (b) numbers ------------------------------------------------------------
    prose: list[tuple[str, str]] = []
    if resume.objective_or_summary:
        prose.append((resume.objective_or_summary, "summary"))
    for edu in resume.education:
        prose.extend((h, f"education/{edu.institution}") for h in edu.highlights)
    for exp in resume.experiences:
        prose.extend((b, f"experience/{exp.organization}") for b in exp.bullets)
    for proj in resume.projects:
        prose.extend((b, f"project/{proj.name}") for b in proj.bullets)
    for text, where in prose:
        for token in extract_numbers(text):
            col.check(
                "b", "number", token, truth.is_supported_number(token, extra_allowed_numbers),
                f"number '{token}' ({where}) does not appear in the profile or facts",
            )

    # --- (c) entities, titles, dates -------------------------------------------
    col.check(
        "c", "name", resume.header.full_name,
        names_match(resume.header.full_name, profile.contact.full_name),
        "candidate name differs from the profile",
    )

    for exp in resume.experiences:
        same_org = [p for p in profile.experiences if names_match(exp.organization, p.organization)]
        col.check(
            "c", "organization", exp.organization, bool(same_org),
            f"organization '{exp.organization}' is not in the profile",
        )
        if not same_org:
            continue
        titled = [p for p in same_org if names_match(exp.title, p.title)]
        col.check(
            "c", "title", f"{exp.title} @ {exp.organization}", bool(titled),
            f"title '{exp.title}' does not match the profile role at {exp.organization}",
        )
        pool = titled or same_org
        col.check(
            "c", "period", f"{exp.period} @ {exp.organization}",
            any(period_matches(exp.period, p.start_date, p.end_date, p.current) for p in pool),
            f"period '{exp.period}' does not match the profile dates at {exp.organization}",
        )

    for edu in resume.education:
        same_inst = [p for p in profile.education if names_match(edu.institution, p.institution)]
        col.check(
            "c", "institution", edu.institution, bool(same_inst),
            f"institution '{edu.institution}' is not in the profile",
        )
        if not same_inst:
            continue
        same_degree = [p for p in same_inst if names_match(edu.degree, p.degree)]
        col.check(
            "c", "degree", f"{edu.degree} @ {edu.institution}", bool(same_degree),
            f"degree '{edu.degree}' does not match the profile for {edu.institution}",
        )
        pool = same_degree or same_inst
        col.check(
            "c", "period", f"{edu.period} @ {edu.institution}",
            any(period_matches(edu.period, p.start_date, p.end_date, p.current) for p in pool),
            f"period '{edu.period}' does not match the profile dates for {edu.institution}",
        )
        known_courses = [c for p in pool for c in (*p.relevant_coursework, *p.highlights)]
        for highlight in edu.highlights:
            match = _COURSEWORK_LABEL_RE.match(highlight)
            if not match:
                continue
            for course in (c.strip() for c in match.group(2).split(",") if c.strip()):
                col.check(
                    "c", "coursework", course,
                    any(names_match(course, known) for known in known_courses),
                    f"course '{course}' is not listed in the profile for {edu.institution}",
                )

    for proj in resume.projects:
        same_name = [p for p in profile.projects if names_match(proj.name, p.name)]
        col.check(
            "c", "project", proj.name, bool(same_name),
            f"project '{proj.name}' is not in the profile",
        )
        if same_name and proj.url and proj.url.strip():
            known_urls = {_normalize_url(p.url) for p in same_name if p.url and p.url.strip()}
            col.check(
                "c", "url", proj.url, _normalize_url(proj.url) in known_urls,
                f"URL '{proj.url}' of project '{proj.name}' is not the profile URL for that project",
            )

    for cert in resume.certifications:
        col.check(
            "c", "certification", cert,
            any(names_match(cert, p.name) for p in profile.certifications),
            f"certification '{cert}' is not in the profile",
        )

    for lang in resume.languages:
        canon = _LANGUAGE_ALIASES.get(lang.language.strip().lower(), lang.language)
        same = [p for p in profile.languages if names_match(canon, p.language)]
        col.check(
            "c", "language", lang.language, bool(same),
            f"language '{lang.language}' is not in the profile",
        )
        if same:
            col.check(
                "c", "proficiency", f"{lang.language}: {lang.proficiency}",
                any(_proficiency_matches(lang.proficiency, p.proficiency) for p in same),
                f"proficiency '{lang.proficiency}' for {lang.language} does not match the profile",
            )

    return col.result()
