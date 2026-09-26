"""Evaluation dataset schemas and loader using Pydantic v2."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from pydantic import BaseModel, ConfigDict, Field
import yaml

from src.data.job_posting import JobPosting


class EvaluationTestCase(BaseModel):
    """Single test case representing an internship position for evaluation.

    Attributes:
        id: Unique identifier for the test case (e.g. 'genai_rag_intern').
        title: Position title.
        company: Hiring organization name.
        location: City and state, or 'Remote'.
        work_model: Modality ('Remote', 'Hybrid', 'On-site').
        target_track: High-level specialization (e.g. 'AI & GenAI', 'Backend').
        technologies: List of required or requested technologies.
        expected_focus: Guidance on what credentials the resume should emphasize.
        ground_truth_criteria: List of factual constraints and anti-hallucination checks.
        description: Full text of the internship announcement.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str = Field(..., description="Unique slug for the test case")
    title: str = Field(..., description="Position title")
    company: str = Field(..., description="Company name")
    location: str = Field(default="São Paulo, SP", description="Job location")
    work_model: str = Field(default="Hybrid", description="Work modality")
    target_track: str = Field(default="General", description="Engineering track")
    technologies: list[str] = Field(default_factory=list, description="Requested technologies")
    expected_focus: str = Field(default="", description="Key focus areas for matching")
    ground_truth_criteria: list[str] = Field(
        default_factory=list,
        description="Factual grounding constraints to verify",
    )
    description: str = Field(..., description="Full job announcement description")

    def to_job_posting(self) -> JobPosting:
        """Convert test case to a JobPosting instance for pipeline execution.

        Returns:
            JobPosting: Configured job posting model ready for retrieval and generation.
        """
        return JobPosting(
            title=self.title,
            company=self.company,
            location=self.location,
            work_model=self.work_model,
            raw_description=self.description,
            technologies=list(self.technologies),
            keywords=list(self.technologies[:5]),
        )


class EvaluationDataset(BaseModel):
    """Collection of evaluation test cases loaded from YAML.

    Attributes:
        test_cases: List of validated EvaluationTestCase instances.
    """

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    test_cases: list[EvaluationTestCase] = Field(
        default_factory=list,
        description="List of evaluation test cases",
    )

    @classmethod
    def from_yaml(cls, path: str | Path) -> EvaluationDataset:
        """Load and validate an evaluation dataset from a YAML file.

        Args:
            path: Path to the dataset YAML file.

        Returns:
            EvaluationDataset: Validated dataset instance.

        Raises:
            FileNotFoundError: If the YAML file is not found.
            ValueError: If YAML structure is invalid.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Evaluation dataset not found at: {file_path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict) or "test_cases" not in data:
            raise ValueError(
                f"Invalid dataset YAML at {file_path}. Expected root dict with 'test_cases'."
            )

        return cls.model_validate(data)

    def get_by_id(self, case_id: str) -> EvaluationTestCase | None:
        """Retrieve a test case by its unique ID.

        Args:
            case_id: Slug ID to search for.

        Returns:
            EvaluationTestCase | None: The matching case or None if not found.
        """
        for tc in self.test_cases:
            if tc.id == case_id:
                return tc
        return None

    def __len__(self) -> int:
        return len(self.test_cases)

    def __iter__(self):
        return iter(self.test_cases)
