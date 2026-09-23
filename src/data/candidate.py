"""Candidate profile schemas using Pydantic v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import yaml


class ContactInfo(BaseModel):
    """Candidate contact and personal identification details.

    Attributes:
        full_name: Candidate's full name.
        email: Contact email address.
        phone: Contact phone number with country/area code.
        location: City and state/country (e.g. 'São Paulo, SP - Brasil').
        linkedin_url: Optional URL to candidate's LinkedIn profile.
        github_url: Optional URL to candidate's GitHub profile.
        portfolio_url: Optional URL to candidate's portfolio or personal website.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    full_name: str = Field(..., description="Full name of the candidate")
    email: str = Field(..., description="Email address")
    phone: str = Field(..., description="Phone number")
    location: str = Field(..., description="City and state/region")
    linkedin_url: str | None = Field(
        default=None,
        description="LinkedIn profile link",
    )
    github_url: str | None = Field(
        default=None,
        description="GitHub profile link",
    )
    portfolio_url: str | None = Field(
        default=None,
        description="Personal portfolio or website link",
    )


class Education(BaseModel):
    """Academic degree or ongoing educational enrollment.

    Attributes:
        institution: University or school name.
        degree: Degree and field of study (e.g., 'Bacharelado em Ciência da Computação').
        start_date: Start date formatted as 'MM/YYYY' or 'YYYY'.
        end_date: Completion date or expected graduation date.
        current: True if currently enrolled.
        gpa_or_honors: Optional academic honors, rank or GPA.
        relevant_coursework: List of relevant disciplines or courses completed.
        highlights: Notable academic activities, scholarships, or research.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    institution: str = Field(..., description="Educational institution name")
    degree: str = Field(..., description="Degree and major field of study")
    start_date: str = Field(..., description="Start date (MM/YYYY)")
    end_date: str = Field(..., description="Graduation date or expected graduation")
    current: bool = Field(default=False, description="Whether currently enrolled")
    gpa_or_honors: str | None = Field(
        default=None,
        description="GPA, honors or academic distinction",
    )
    relevant_coursework: list[str] = Field(
        default_factory=list,
        description="Relevant academic courses",
    )
    highlights: list[str] = Field(
        default_factory=list,
        description="Academic awards, scholarships or achievements",
    )


class Experience(BaseModel):
    """Professional, internship, or academic employment experience.

    Attributes:
        title: Job or role title.
        organization: Company, laboratory or institution name.
        location: City and state, or 'Remoto'.
        start_date: Start date formatted as 'MM/YYYY'.
        end_date: End date formatted as 'MM/YYYY' or 'Presente'.
        current: True if this is the candidate's current role.
        bullets: Action-oriented achievement bullet points.
        technologies: Technologies and tools used in this role.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(..., description="Role or position title")
    organization: str = Field(..., description="Company or organization name")
    location: str | None = Field(default=None, description="Location or Remote")
    start_date: str = Field(..., description="Start date (MM/YYYY)")
    end_date: str = Field(default="Presente", description="End date (MM/YYYY or Presente)")
    current: bool = Field(default=False, description="Whether this is the current job")
    bullets: list[str] = Field(
        default_factory=list,
        description="Bullet points describing responsibilities and achievements",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Technologies and methodologies utilized",
    )


class Project(BaseModel):
    """Personal, open-source or academic project.

    Attributes:
        name: Name of the project.
        description: Brief summary of the project purpose.
        url: Optional repository or live demo link.
        bullets: Key features, accomplishments, or implementation highlights.
        technologies: Technologies, libraries and frameworks used.
        highlight: Whether to give high priority to this project in resumes.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Short project overview")
    url: str | None = Field(default=None, description="Project link or repository")
    bullets: list[str] = Field(
        default_factory=list,
        description="Bullet points highlighting features and impact",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Stack and technologies used",
    )
    highlight: bool = Field(
        default=False,
        description="Whether this project is a top highlight",
    )


class Language(BaseModel):
    """Spoken or written language proficiency.

    Attributes:
        language: Language name (e.g. 'Inglês', 'Espanhol').
        proficiency: CEFR level or descriptive fluency (e.g. 'Avançado (C1)').
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    language: str = Field(..., description="Language name")
    proficiency: str = Field(..., description="Proficiency level")


class Certification(BaseModel):
    """Professional license, certificate or course credential.

    Attributes:
        name: Certificate or course name.
        issuer: Organization that issued the credential.
        issue_date: Optional issue date (MM/YYYY).
        url: Optional credential verification URL.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    name: str = Field(..., description="Certificate name")
    issuer: str = Field(..., description="Issuing organization")
    issue_date: str | None = Field(default=None, description="Date of issuance")
    url: str | None = Field(default=None, description="Credential URL")


class Skills(BaseModel):
    """Categorized technical and soft skills of the candidate.

    Attributes:
        programming_languages: Programming languages known.
        frameworks_and_libraries: Frameworks, SDKs and libraries.
        databases: Database management systems and storage tools.
        tools_and_platforms: DevOps, cloud, OS, and productivity tools.
        soft_skills: Interpersonal, communication and problem-solving skills.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    programming_languages: list[str] = Field(
        default_factory=list,
        description="Programming languages (e.g. Python, SQL, C++)",
    )
    frameworks_and_libraries: list[str] = Field(
        default_factory=list,
        description="Libraries and frameworks (e.g. PyTorch, FastAPI, React)",
    )
    databases: list[str] = Field(
        default_factory=list,
        description="Databases (e.g. PostgreSQL, ChromaDB, Redis)",
    )
    tools_and_platforms: list[str] = Field(
        default_factory=list,
        description="Tools and platforms (e.g. Git, Docker, Linux)",
    )
    soft_skills: list[str] = Field(
        default_factory=list,
        description="Interpersonal and behavioral skills",
    )


class CandidateProfile(BaseModel):
    """Aggregated candidate profile containing all experiences and credentials.

    Attributes:
        contact: Personal and contact information.
        summary: Optional default professional summary or bio.
        education: List of educational qualifications.
        experiences: List of professional or academic experiences.
        projects: List of technical projects.
        skills: Categorized skills.
        languages: List of languages and proficiencies.
        certifications: List of certifications and licenses.
        additional_info: Extracurriculars, hackathons, volunteering, etc.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    contact: ContactInfo
    summary: str | None = Field(
        default=None,
        description="General bio or career objective",
    )
    education: list[Education] = Field(
        default_factory=list,
        description="Educational background",
    )
    experiences: list[Experience] = Field(
        default_factory=list,
        description="Work and research experiences",
    )
    projects: list[Project] = Field(
        default_factory=list,
        description="Portfolio projects",
    )
    skills: Skills = Field(
        default_factory=Skills,
        description="Categorized technical and interpersonal skills",
    )
    languages: list[Language] = Field(
        default_factory=list,
        description="Spoken and written languages",
    )
    certifications: list[Certification] = Field(
        default_factory=list,
        description="Professional certifications",
    )
    additional_info: list[str] = Field(
        default_factory=list,
        description="Extracurricular activities, volunteering or awards",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> CandidateProfile:
        """Load and validate candidate profile from a YAML file.

        Args:
            path: Path to the candidate profile YAML file.

        Returns:
            CandidateProfile: Validated candidate profile instance.

        Raises:
            FileNotFoundError: If the YAML file does not exist.
            ValueError: If parsing or validation fails.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Candidate profile not found at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            raw_data = yaml.safe_load(f)

        if not isinstance(raw_data, dict):
            raise ValueError(
                f"Invalid YAML structure at {file_path}. Expected a key-value dictionary."
            )

        return cls.model_validate(raw_data)

    def to_yaml(self, path: str | Path) -> None:
        """Export candidate profile to a YAML file.

        Args:
            path: Destination file path.
        """
        dest_path = Path(path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        dumped_dict = self.model_dump(exclude_none=True)
        with open(dest_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(dumped_dict, f, allow_unicode=True, sort_keys=False)
