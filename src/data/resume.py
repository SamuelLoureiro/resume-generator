"""Resume generation schema and LaTeX rendering data structures using Pydantic v2."""

from __future__ import annotations

import re
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator

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


def escape_latex(text: str) -> str:
    """Escape special LaTeX characters in a plain text string.

    Args:
        text: Plain text input.

    Returns:
        str: Text safe to inject into LaTeX templates.
    """
    if not text:
        return ""

    # Replace backslash first if needed, then other reserved characters
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

    # Use regex to substitute safely
    pattern = re.compile("|".join(re.escape(k) for k in replacements.keys()))
    return pattern.sub(lambda m: replacements[m.group(0)], str(text))


def _deep_escape(data: Any) -> Any:
    """Recursively escape strings inside nested dictionaries and lists."""
    if isinstance(data, str):
        return escape_latex(data)
    elif isinstance(data, list):
        return [_deep_escape(item) for item in data]
    elif isinstance(data, dict):
        return {k: _deep_escape(v) for k, v in data.items()}
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
        proficiency: Fluency level.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    language: str = Field(..., description="Language name")
    proficiency: str = Field(..., description="Fluency descriptor")


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
