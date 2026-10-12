"""Job posting schema using Pydantic v2."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class JobPosting(BaseModel):
    """Internship job description and requirements structure.

    Attributes:
        title: Title of the internship position (e.g. 'Machine Learning Engineering Intern').
        company: Name of the hiring company or organization.
        location: City, state or 'Remote / Brazil'.
        work_model: Work modality ('On-site', 'Hybrid', 'Remote').
        raw_description: Full text description provided by the user.
        requirements: List of mandatory requirements or qualifications.
        desirables: List of nice-to-have or preferred skills.
        responsibilities: Key responsibilities or day-to-day tasks.
        technologies: Explicit technologies and tools requested in the job.
        keywords: Relevant industry or domain keywords.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    title: str = Field(..., description="Internship position title")
    company: str = Field(..., description="Hiring company name")
    location: str | None = Field(default=None, description="Job location")
    work_model: str | None = Field(
        default="Hybrid",
        description="Work model: Remote, Hybrid, or On-site",
    )
    raw_description: str = Field(
        ...,
        description="Full raw text of the internship announcement",
    )
    requirements: list[str] = Field(
        default_factory=list,
        description="Mandatory skills and prerequisites",
    )
    desirables: list[str] = Field(
        default_factory=list,
        description="Preferred or nice-to-have qualifications",
    )
    responsibilities: list[str] = Field(
        default_factory=list,
        description="Core duties and day-to-day activities",
    )
    technologies: list[str] = Field(
        default_factory=list,
        description="Tech stack and tools mentioned in the job description",
    )
    keywords: list[str] = Field(
        default_factory=list,
        description="Extracted keywords for ATS and semantic matching",
    )

    def to_search_query(self) -> str:
        """Generate an optimized search query for RAG retrieval.

        Combines title, mandatory requirements, and technologies into a query
        suitable for similarity search in the vector store and knowledge base.

        Returns:
            str: Semantic query string.
        """
        title_str = self.title.strip() if self.title else "Internship"
        comp_str = f" at {self.company.strip()}" if self.company and self.company.strip() else ""
        parts = [f"Job: {title_str}{comp_str}"]

        if self.technologies:
            clean_techs = [t.strip() for t in self.technologies if t and t.strip()]
            if clean_techs:
                parts.append(f"Technologies: {', '.join(clean_techs)}")

        if self.requirements:
            clean_reqs = [r.strip() for r in self.requirements if r and r.strip()]
            if clean_reqs:
                parts.append(f"Requirements: {'; '.join(clean_reqs[:5])}")

        if self.keywords:
            clean_keys = [k.strip() for k in self.keywords if k and k.strip()]
            if clean_keys:
                parts.append(f"Keywords: {', '.join(clean_keys[:5])}")

        return "\n".join(parts)

    def to_prompt_context(self) -> str:
        """Format the job posting as structured text for LLM prompts.

        Returns:
            str: Clean text representation for injection in prompt templates.
        """
        lines = [
            f"**Role:** {self.title}",
            f"**Company:** {self.company}",
        ]
        if self.location:
            lines.append(f"**Location/Model:** {self.location} ({self.work_model})")

        if self.requirements:
            lines.append("\n**Mandatory Requirements:**")
            for req in self.requirements:
                lines.append(f"- {req}")

        if self.desirables:
            lines.append("\n**Nice-to-Have / Preferred:**")
            for des in self.desirables:
                lines.append(f"- {des}")

        if self.responsibilities:
            lines.append("\n**Main Responsibilities:**")
            for resp in self.responsibilities:
                lines.append(f"- {resp}")

        if self.technologies:
            lines.append(f"\n**Tech Stack:** {', '.join(self.technologies)}")

        lines.append(f"\n**Full Description:**\n{self.raw_description.strip()}")

        return "\n".join(lines)

