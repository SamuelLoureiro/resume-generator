"""Job posting schema using Pydantic v2."""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, ConfigDict, Field


class JobPosting(BaseModel):
    """Internship job description and requirements structure.

    Attributes:
        title: Title of the internship position (e.g. 'Estágio em Inteligência Artificial').
        company: Name of the hiring company or organization.
        location: City, state or 'Remoto / Brasil'.
        work_model: Work modality ('Presencial', 'Híbrido', 'Remoto').
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
        default="Híbrido",
        description="Work model: Remoto, Híbrido, or Presencial",
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
        parts = [f"Vaga: {self.title} na empresa {self.company}"]

        if self.technologies:
            parts.append(f"Tecnologias: {', '.join(self.technologies)}")

        if self.requirements:
            parts.append(f"Requisitos: {'; '.join(self.requirements[:5])}")

        if self.keywords:
            parts.append(f"Palavras-chave: {', '.join(self.keywords[:5])}")

        return "\n".join(parts)

    def to_prompt_context(self) -> str:
        """Format the job posting as structured text for LLM prompts.

        Returns:
            str: Clean text representation for injection in prompt templates.
        """
        lines = [
            f"**Cargo:** {self.title}",
            f"**Empresa:** {self.company}",
        ]
        if self.location:
            lines.append(f"**Localização/Modelo:** {self.location} ({self.work_model})")

        if self.requirements:
            lines.append("\n**Requisitos Obrigatórios:**")
            for req in self.requirements:
                lines.append(f"- {req}")

        if self.desirables:
            lines.append("\n**Diferenciais / Desejáveis:**")
            for des in self.desirables:
                lines.append(f"- {des}")

        if self.responsibilities:
            lines.append("\n**Principais Atividades:**")
            for resp in self.responsibilities:
                lines.append(f"- {resp}")

        if self.technologies:
            lines.append(f"\n**Stack Técnica:** {', '.join(self.technologies)}")

        lines.append(f"\n**Descrição Completa:**\n{self.raw_description.strip()}")

        return "\n".join(lines)
