"""Resume generation schema and LaTeX rendering data structures using Pydantic v2."""

from __future__ import annotations

import re
from typing import Any, Literal, Self
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ResumeLanguageCode = Literal["pt", "en", "fr"]

SECTION_LABELS: dict[str, dict[str, str]] = {
    "pt": {
        "objective": "Objetivo Profissional",
        "education": "Formação Acadêmica",
        "experience": "Experiência Profissional",
        "projects": "Projetos em Destaque",
        "skills": "Habilidades Técnicas",
        "languages_certs": "Idiomas & Certificações",
        "languages_only": "Idiomas",
        "certifications_only": "Certificações",
        "technologies": "Tecnologias:",
        "stack": "Stack:",
        "view_project": "[Ver Projeto / Repositório]",
        "languages": "Idiomas:",
        "certifications": "Certificações:",
        "present": "Presente",
    },
    "en": {
        "objective": "Professional Summary",
        "education": "Education",
        "experience": "Work Experience",
        "projects": "Featured Projects",
        "skills": "Technical Skills",
        "languages_certs": "Languages & Certifications",
        "languages_only": "Languages",
        "certifications_only": "Certifications",
        "technologies": "Technologies:",
        "stack": "Stack:",
        "view_project": "[View Project / Code]",
        "languages": "Languages:",
        "certifications": "Certifications:",
        "present": "Present",
    },
    "fr": {
        "objective": "Profil Professionnel",
        "education": "Formation",
        "experience": "Expérience Professionnelle",
        "projects": "Projets Notables",
        "skills": "Compétences Techniques",
        "languages_certs": "Langues & Certifications",
        "languages_only": "Langues",
        "certifications_only": "Certifications",
        "technologies": "Technologies :",
        "stack": "Stack :",
        "view_project": "[Voir le projet / Dépôt]",
        "languages": "Langues :",
        "certifications": "Certifications :",
        "present": "Présent",
    },
}


def format_language_entry(
    language: str,
    level: str | None = None,
    certificate: str | None = None,
    proficiency: str | None = None,
) -> str:
    """Build a standardized language display string with certificate in parentheses exactly once.

    Args:
        language: Language name (e.g. 'English', 'French').
        level: Optional structured proficiency level (e.g. 'Native', 'B2', 'Advanced').
        certificate: Optional certificate info (e.g. 'TOEIC', 'TOEIC 945').
        proficiency: Legacy fallback proficiency string.

    Returns:
        str: Formatted language entry string, e.g. 'English (B2) (TOEIC)' or 'Portuguese (Native)'.
    """
    lang = language.strip()

    raw_level = (level or "").strip()
    raw_cert = (certificate or "").strip()

    # If structured fields not provided, inspect legacy proficiency
    if not raw_level and not raw_cert and proficiency:
        raw_prof = proficiency.strip()
        # Clean any accidental double parentheses, e.g. ((TOEIC...)) -> (TOEIC...)
        raw_prof = re.sub(r"\(\(\s*(.*?)\s*\)\)", r"(\1)", raw_prof)
        # Check for two separate parentheses e.g. "(B2) (TOEIC)" or "B2 (TOEIC)"
        two_paren_match = re.match(
            r"^(?:(?:\((?P<p1>[^)]+)\))|(?P<p1_bare>[^(]+?))\s*\((?P<p2>(?:TOEIC|TOEFL|IELTS|Cambridge|Cert)[^)]*)\)$",
            raw_prof,
            re.IGNORECASE,
        )
        if two_paren_match:
            raw_level = (two_paren_match.group("p1") or two_paren_match.group("p1_bare")).strip()
            raw_cert = two_paren_match.group("p2").strip()
        else:
            raw_level = raw_prof

    # Strip outer parentheses from certificate if passed with them
    clean_cert = re.sub(r"^[(\s]+|[)\s]+$", "", raw_cert)

    # Strip outer parentheses from level if the ENTIRE level is enclosed
    clean_level = raw_level
    if clean_level.startswith("(") and clean_level.endswith(")") and clean_level.count("(") == 1:
        clean_level = clean_level[1:-1].strip()

    if clean_cert:
        # Check if clean_level already contains clean_cert in parens
        if f"({clean_cert})" in clean_level:
            clean_level = re.sub(r"\(\(\s*(.*?)\s*\)\)", r"(\1)", clean_level)
            return (
                f"{lang} ({clean_level})"
                if not (clean_level.startswith("(") and clean_level.endswith(")"))
                else f"{lang} {clean_level}"
            )
        if clean_level:
            return f"{lang} ({clean_level}) ({clean_cert})"
        return f"{lang} ({clean_cert})"
    elif clean_level:
        if clean_level.startswith("(") and clean_level.endswith(")"):
            return f"{lang} {clean_level}"
        return f"{lang} ({clean_level})"
    return lang


def convert_typographic_quotes(text: str) -> str:
    """Convert straight quotes and apostrophes to typographic equivalents.

    Converts:
        - "..." -> “...”
        - ' -> ’ (in contractions/possessives: candidate's, don't)
        - '...' -> ‘...’ (quoted phrases)

    Preserves:
        - \\' (LaTeX accents like \\'e)
        - URLs (https://..., http://...)

    Args:
        text: Plain or lightly-marked text.

    Returns:
        str: Text with typographic quotes and apostrophes.
    """
    if not text:
        return ""

    protected = re.compile(
        r"https?://[^\s<>{}\"]+"  # URLs
        r"|\\'"                    # LaTeX accent \'
    )

    parts: list[tuple[str, str]] = []
    last_end = 0
    for m in protected.finditer(text):
        if m.start() > last_end:
            parts.append(("text", text[last_end:m.start()]))
        parts.append(("protected", m.group(0)))
        last_end = m.end()
    if last_end < len(text):
        parts.append(("text", text[last_end:]))

    out: list[str] = []
    for kind, val in parts:
        if kind == "protected":
            out.append(val)
        else:
            # 1. Double quotes: "..." -> “...”
            s = re.sub(r'"([^"\n]*)"', r'“\1”', val)
            s = re.sub(r'(^|[\s(\[])"', r'\1“', s)
            s = s.replace('"', '”')
            # 2. Paired single quotes: '...' -> ‘...’
            s = re.sub(r"(^|[\s(\[])'([^'\n]+)'(?=[\s)\].,;:!?]|$)", r"\1‘\2’", s)
            # 3. Apostrophes: ' -> ’
            s = s.replace("'", "’")
            out.append(s)
    return "".join(out)


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in a plain text string.

    Converts straight apostrophes and quotes to typographic equivalents,
    while escaping reserved LaTeX characters and preserving accents/commands/URLs.

    Args:
        text: Plain text input.

    Returns:
        str: Text safe to inject into LaTeX templates.
    """
    if not text:
        return ""

    # First apply typographic quote conversion
    text = convert_typographic_quotes(str(text))

    # Protect \' and URLs so \' does not become \textbackslash{}'
    protected = re.compile(r"https?://[^\s<>{}\"]+|\\'")

    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
        "—": "---",
        "–": "--",
    }
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))

    parts: list[str] = []
    last_end = 0
    for m in protected.finditer(text):
        if m.start() > last_end:
            chunk = text[last_end:m.start()]
            parts.append(pattern.sub(lambda match: replacements[match.group(0)], chunk))
        parts.append(m.group(0))
        last_end = m.end()
    if last_end < len(text):
        chunk = text[last_end:]
        parts.append(pattern.sub(lambda match: replacements[match.group(0)], chunk))

    return "".join(parts)


def _deep_escape(data: Any, key: str | None = None) -> Any:
    """Recursively escape strings inside nested dictionaries and lists."""
    if isinstance(data, str):
        if key and (key == "url" or key.endswith("_url")):
            return data
        return escape_latex(data)
    elif isinstance(data, list):
        return [_deep_escape(item, key=key) for item in data]
    elif isinstance(data, dict):
        return {k: _deep_escape(v, key=k) for k, v in data.items()}
    return data


class ResumeHeader(BaseModel):
    """Personal and contact info formatted for resume header.

    Attributes:
        full_name: Candidate full name.
        email: Contact email address.
        phone: Contact phone number.
        location: City and state.
        linkedin_url: Clean or full LinkedIn URL.
        github_url: Clean or full GitHub URL.
        portfolio_url: Optional website link.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    full_name: str = Field(default="", description="Candidate full name")
    email: str = Field(default="", description="Email address")
    phone: str = Field(default="", description="Phone number")
    location: str = Field(default="", description="Location")
    linkedin_url: str | None = Field(default=None, description="LinkedIn URL")
    github_url: str | None = Field(default=None, description="GitHub URL")
    portfolio_url: str | None = Field(default=None, description="Portfolio URL")

    @field_validator("linkedin_url", "github_url", "portfolio_url", mode="before")
    @classmethod
    def ensure_url_scheme(cls, v: Any) -> Any:
        """Prepend https:// if URL is provided without protocol scheme."""
        if isinstance(v, str) and v.strip():
            cleaned = v.strip()
            if not cleaned.startswith(("http://", "https://")):
                return f"https://{cleaned}"
            return cleaned
        return v


class ResumeEducation(BaseModel):
    """Education entry selected and formatted for the resume.

    Attributes:
        institution: College or university name.
        degree: Degree, major and status.
        period: Timeframe (e.g. '03/2023 - 12/2026').
        location: Institution location if applicable.
        highlights: Relevant coursework, GPA or awards.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    institution: str = Field(..., description="University name")
    degree: str = Field(..., description="Degree and major")
    period: str = Field(..., description="Start and graduation dates")
    location: str | None = Field(default=None, description="City/State")
    highlights: list[str] = Field(
        default_factory=list,
        description="Relevant academic highlights or coursework",
    )

    @field_validator("institution", mode="before")
    @classmethod
    def shorten_institution_names(cls, v: Any) -> Any:
        """Shorten known overly long institution names so education headers fit on one line at 10pt A4."""
        if isinstance(v, str):
            if "École Nationale d'Ingénieurs de Brest" in v:
                return "ENIB"
        return v


class ResumeExperience(BaseModel):
    """Professional or extracurricular experience entry.

    Attributes:
        title: Position or role title.
        organization: Organization or company name.
        period: Start and end dates.
        location: City and state or 'Remote'.
        bullets: Action-oriented bullet points tailored to the job.
        technologies: Tech stack tags for the experience.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(..., description="Role title")
    organization: str = Field(..., description="Company name")
    period: str = Field(..., description="Date range")
    location: str | None = Field(default=None, description="Location or Remote")
    bullets: list[str] = Field(
        default_factory=list,
        description="Tailored accomplishment bullet points",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies highlighted in this role",
    )


class ResumeProject(BaseModel):
    """Selected project highlighted for relevance to the job.

    Attributes:
        name: Name of the project.
        technologies: Stack used in the project.
        url: Repository or demo link.
        bullets: Impact or feature bullet points.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., description="Project title")
    technologies: list[str] = Field(
        default_factory=list,
        description="Key technologies used",
    )
    url: str | None = Field(default=None, description="Project link")
    bullets: list[str] = Field(
        default_factory=list,
        description="Action bullets demonstrating technical competence",
    )

    @field_validator("url", mode="before")
    @classmethod
    def ensure_url_scheme(cls, v: Any) -> Any:
        """Prepend https:// if URL is provided without protocol scheme."""
        if isinstance(v, str) and v.strip():
            cleaned = v.strip()
            if not cleaned.startswith(("http://", "https://")):
                return f"https://{cleaned}"
            return cleaned
        return v


class ResumeSkillCategory(BaseModel):
    """Grouped skill category for clean resume display.

    Attributes:
        category_name: Section label (e.g. 'Programming Languages').
        skills: List of skill names.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    category_name: str = Field(..., description="Category heading")
    skills: list[str] = Field(
        default_factory=list,
        description="List of skills in this category",
    )


class ResumeLanguage(BaseModel):
    """Language entry for the resume.

    Attributes:
        language: Language name.
        proficiency: Fluency descriptor.
        level: Optional structured proficiency level (e.g. 'Native', 'B2', 'Advanced').
        certificate: Optional certificate info (e.g. 'TOEIC', 'TOEIC 945').
        formatted: Formatted string ready for display.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    language: str = Field(..., description="Language name")
    proficiency: str = Field(default="", description="Fluency descriptor")
    level: str | None = Field(default=None, description="Proficiency level (e.g. Native, B2, C1)")
    certificate: str | None = Field(default=None, description="Certificate details (e.g. TOEIC)")
    formatted: str = Field(
        default="",
        description="Formatted language line with certificate in parens exactly once",
    )

    @model_validator(mode="after")
    def populate_formatted_and_proficiency(self) -> Self:
        """Ensure formatted and proficiency strings are populated and clean."""
        if not self.formatted:
            self.formatted = format_language_entry(
                language=self.language,
                level=self.level,
                certificate=self.certificate,
                proficiency=self.proficiency,
            )
        if not self.proficiency:
            if self.level and self.certificate:
                clean_cert = re.sub(r"^[(\s]+|[)\s]+$", "", self.certificate)
                self.proficiency = f"{self.level} ({clean_cert})"
            elif self.level:
                self.proficiency = self.level
            elif self.certificate:
                clean_cert = re.sub(r"^[(\s]+|[)\s]+$", "", self.certificate)
                self.proficiency = f"({clean_cert})"
        return self

    def format_line(self) -> str:
        """Format language line with certificate in parentheses exactly once."""
        return self.formatted or format_language_entry(
            language=self.language,
            level=self.level,
            certificate=self.certificate,
            proficiency=self.proficiency,
        )


class TailoredResume(BaseModel):
    """Complete tailored resume data ready for LaTeX compilation.

    Attributes:
        target_job_title: The internship job title being applied for.
        target_company: The hiring company name.
        header: Candidate header details.
        objective_or_summary: Brief professional summary or objective tailored to the role.
        education: Academic background.
        experiences: Selected and tailored experiences.
        projects: Selected and tailored portfolio projects.
        skills: Categorized technical and soft skills.
        languages: Language proficiencies.
        certifications: Selected certifications and awards.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    target_job_title: str = Field(
        ...,
        description="Internship position being targeted",
    )
    target_company: str = Field(
        ...,
        description="Hiring company targeted",
    )
    header: ResumeHeader
    objective_or_summary: str | None = Field(
        default=None,
        description="Tailored career objective or summary",
    )
    education: list[ResumeEducation] = Field(
        default_factory=list,
        description="Education section entries",
    )
    experiences: list[ResumeExperience] = Field(
        default_factory=list,
        description="Experience section entries",
    )
    projects: list[ResumeProject] = Field(
        default_factory=list,
        description="Project section entries",
    )
    skills: list[ResumeSkillCategory] = Field(
        default_factory=list,
        description="Categorized skills entries",
    )
    languages: list[ResumeLanguage] = Field(
        default_factory=list,
        description="Languages list",
    )
    certifications: list[str] = Field(
        default_factory=list,
        description="Certifications list",
    )
    language: ResumeLanguageCode = Field(
        default="pt",
        description="Language of the resume (pt, en, fr)",
    )

    def to_latex_context(self) -> dict[str, Any]:
        """Convert resume to a dictionary with all strings escaped for LaTeX.

        Returns:
            dict[str, Any]: Dictionary ready to be passed to Jinja2 LaTeX template.
        """
        raw_dict = self.model_dump()
        escaped = _deep_escape(raw_dict)
        labels = SECTION_LABELS.get(self.language, SECTION_LABELS["pt"])
        escaped["labels"] = _deep_escape(labels)
        return escaped
