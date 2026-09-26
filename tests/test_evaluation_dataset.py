"""Unit tests for evaluation dataset, facts formatter, and benchmark runner."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.data.candidate import CandidateProfile
from src.data.evaluation import EvaluationDataset, EvaluationTestCase
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.evaluation.benchmark import (
    EvaluationBenchmark,
    format_candidate_facts,
    format_resume_as_text,
    format_resume_claims,
)
from src.evaluation.metrics import EvaluationScores
from src.evaluation.runner import EvaluationRunResult, EvaluationRunner, EvaluationSample


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    """Load the default verified candidate profile."""
    return CandidateProfile.from_yaml("data/candidate_profile.yaml")


@pytest.fixture
def sample_tailored_resume() -> TailoredResume:
    """Construct a minimal valid TailoredResume for formatting tests."""
    return TailoredResume(
        header=ResumeHeader(
            full_name="Samuel Amadeu Loureiro",
            email="samu.loureiro23@gmail.com",
            phone="+33 743528487",
            location="Brest - France",
            linkedin_url="www.linkedin.com/in/samuelamadeuloureiro",
            github_url="https://github.com/SamuelLoureiro",
        ),
        target_job_title="AI Engineering Intern",
        target_company="NeuralWave Labs",
        objective_or_summary="Aspiring AI Engineer motivated to contribute to NeuralWave Labs.",
        education=[
            ResumeEducation(
                institution="UNIFEI",
                degree="BSc Computer Engineering",
                period="03/2022 - 12/2027",
                highlights=["GPA 8.5/10.0", "Coursework: Artificial Intelligence, Data Structures"],
            )
        ],
        experiences=[
            ResumeExperience(
                title="AI & NLP Researcher",
                organization="UNIFEI Computational Intelligence Lab",
                period="08/2024 - Present",
                bullets=["Developed text processing pipelines with PyTorch and LlamaIndex."],
                technologies=["Python", "PyTorch", "LlamaIndex"],
            )
        ],
        projects=[
            ResumeProject(
                name="Resume Generator RAG",
                bullets=["Implemented hybrid vector and keyword search."],
                technologies=["Python", "ChromaDB", "LlamaIndex"],
            )
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Languages & Frameworks",
                skills=["Python", "PyTorch", "FastAPI", "LlamaIndex"],
            )
        ],
        languages=[
            ResumeLanguage(language="Portuguese", proficiency="Native"),
            ResumeLanguage(language="English", proficiency="Advanced (C1)"),
        ],
    )


# ---------------------------------------------------------------------------
# Dataset loading & schema tests
# ---------------------------------------------------------------------------


def test_evaluation_dataset_load_real_file() -> None:
    """Verify loading the real data/eval/evaluation_dataset.yaml file."""
    dataset = EvaluationDataset.from_yaml("data/eval/evaluation_dataset.yaml")
    assert len(dataset) == 5

    expected_ids = [
        "genai_rag_intern",
        "data_science_ml_intern",
        "backend_python_intern",
        "swe_algorithms_intern",
        "data_engineering_intern",
    ]

    for expected_id in expected_ids:
        tc = dataset.get_by_id(expected_id)
        assert tc is not None
        assert tc.id == expected_id
        assert len(tc.title) > 0
        assert len(tc.company) > 0
        assert len(tc.technologies) > 0
        assert len(tc.description) > 50
        assert len(tc.ground_truth_criteria) > 0


def test_evaluation_dataset_missing_file_raises(tmp_path: Path) -> None:
    """Test loading non-existent YAML file raises FileNotFoundError."""
    missing = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        EvaluationDataset.from_yaml(missing)


def test_evaluation_dataset_invalid_yaml_structure_raises(tmp_path: Path) -> None:
    """Test invalid YAML without 'test_cases' raises ValueError."""
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("invalid_key: 123", encoding="utf-8")
    with pytest.raises(ValueError, match="test_cases"):
        EvaluationDataset.from_yaml(bad_file)


def test_evaluation_test_case_to_job_posting() -> None:
    """Test converting EvaluationTestCase to JobPosting."""
    tc = EvaluationTestCase(
        id="test_case",
        title="ML Intern",
        company="DeepMind",
        location="London, UK",
        work_model="Hybrid",
        target_track="AI",
        technologies=["Python", "PyTorch", "JAX"],
        description="Machine learning research internship.",
    )
    job = tc.to_job_posting()
    assert isinstance(job, JobPosting)
    assert job.title == "ML Intern"
    assert job.company == "DeepMind"
    assert job.location == "London, UK"
    assert "Python" in job.technologies
    assert "Python" in job.to_search_query()


# ---------------------------------------------------------------------------
# Formatting helpers tests
# ---------------------------------------------------------------------------


def test_format_candidate_facts(sample_candidate: CandidateProfile) -> None:
    """Test that format_candidate_facts covers all verified background sections."""
    facts = format_candidate_facts(sample_candidate)

    assert "Samuel Amadeu Loureiro" in facts
    assert "samu.loureiro23@gmail.com" in facts
    assert "Universidade Federal de Itajubá (UNIFEI)" in facts
    assert "Laboratório de Inteligência Computacional" in facts
    assert "Gerador de Currículos com RAG" in facts
    assert "LlamaIndex" in facts
    assert "Python" in facts
    assert "Português" in facts


def test_format_resume_as_text(sample_tailored_resume: TailoredResume) -> None:
    """Test that format_resume_as_text converts resume into clean text."""
    text = format_resume_as_text(sample_tailored_resume)

    assert "Samuel Amadeu Loureiro" in text
    assert "AI Engineering Intern @ NeuralWave Labs" in text
    assert "UNIFEI" in text
    assert "AI & NLP Researcher" in text
    assert "Resume Generator RAG" in text
    assert "Languages & Frameworks" in text
    assert "Portuguese" in text


def test_format_resume_claims(sample_tailored_resume: TailoredResume) -> None:
    """Test that format_resume_claims extracts only factual credentials."""
    claims = format_resume_claims(sample_tailored_resume)

    assert "UNIFEI" in claims
    assert "AI & NLP Researcher" in claims
    assert "Resume Generator RAG" in claims
    assert "Languages & Frameworks" in claims
    # Target company metadata must NOT be in factual claims
    assert "NeuralWave Labs" not in claims


# ---------------------------------------------------------------------------
# Benchmark execution tests (Mocked)
# ---------------------------------------------------------------------------


def test_evaluation_benchmark_run_test_case_mocked(
    sample_candidate: CandidateProfile,
    sample_tailored_resume: TailoredResume,
) -> None:
    """Test running a single benchmark test case with mocked pipeline and chain."""
    mock_pipeline = MagicMock()
    mock_node = MagicMock()
    mock_node.score = 0.85
    mock_node.node.metadata = {"category": "Best Practice", "topic": "STAR Method"}
    mock_node.node.get_content.return_value = "Use STAR method and quantify results."
    mock_pipeline.retrieve_for_job.return_value = [mock_node]

    mock_chain = MagicMock()
    mock_chain.generate.return_value = sample_tailored_resume

    mock_runner = MagicMock()
    mock_runner.evaluate_sample.return_value = EvaluationRunResult(
        sample=EvaluationSample(
            query="AI Engineer",
            retrieved_contexts=["Context 1"],
            generated_response="Resume text",
            candidate_facts="Facts",
            job_title="AI Intern",
            company="Startup",
        ),
        scores=EvaluationScores(faithfulness=0.95, answer_relevancy=0.88, context_precision=0.80),
    )

    benchmark = EvaluationBenchmark(
        pipeline=mock_pipeline,
        chain=mock_chain,
        runner=mock_runner,
    )

    tc = EvaluationTestCase(
        id="test_run",
        title="AI Engineer",
        company="Startup",
        description="Build GenAI apps.",
        technologies=["Python", "LlamaIndex"],
    )

    result = benchmark.run_test_case(tc, candidate=sample_candidate, top_k=3)

    assert result.success
    assert result.scores.faithfulness == 0.95
    assert result.scores.answer_relevancy == 0.88
    assert result.scores.context_precision == 0.80
    mock_pipeline.retrieve_for_job.assert_called_once()
    mock_chain.generate.assert_called_once()
    mock_runner.evaluate_sample.assert_called_once()


def test_evaluation_benchmark_run_benchmark_filtering(
    sample_candidate: CandidateProfile,
    sample_tailored_resume: TailoredResume,
    tmp_path: Path,
) -> None:
    """Test running benchmark with case filtering and saving report."""
    dataset = EvaluationDataset.from_yaml("data/eval/evaluation_dataset.yaml")

    mock_pipeline = MagicMock()
    mock_node = MagicMock()
    mock_node.score = 0.85
    mock_node.node.metadata = {"category": "Best Practice", "topic": "STAR Method"}
    mock_node.node.get_content.return_value = "Guidelines text"
    mock_pipeline.retrieve_for_job.return_value = [mock_node]

    mock_chain = MagicMock()
    mock_chain.generate.return_value = sample_tailored_resume

    mock_runner = MagicMock()
    mock_runner.evaluate_sample.return_value = EvaluationRunResult(
        sample=EvaluationSample(
            query="Query",
            retrieved_contexts=["Context"],
            generated_response="Response",
            candidate_facts="Facts",
            job_title="Test Job",
            company="Test Co",
        ),
        scores=EvaluationScores(faithfulness=1.0, answer_relevancy=0.9, context_precision=0.85),
    )

    benchmark = EvaluationBenchmark(
        pipeline=mock_pipeline,
        chain=mock_chain,
        runner=mock_runner,
    )

    # Filter to run only 2 specific cases
    results = benchmark.run_benchmark(
        dataset=dataset,
        candidate=sample_candidate,
        top_k=2,
        test_case_ids=["genai_rag_intern", "backend_python_intern"],
    )

    assert len(results) == 2
    assert all(r.success for r in results)

    # Test saving report
    report_file = tmp_path / "evaluation.md"
    report_content = benchmark.save_report(results, output_path=report_file)
    assert report_file.exists()
    assert "# 📊 RAG Pipeline Evaluation Report" in report_content
    assert "Faithfulness" in report_content
