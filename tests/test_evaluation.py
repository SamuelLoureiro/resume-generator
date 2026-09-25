"""Unit tests for the evaluation module (src/evaluation/).

All tests are fully offline — no real LLM or API calls are made.
Evaluator methods are patched via unittest.mock to return fixed
EvaluationResult objects, isolating the evaluation business logic
from the underlying LLM infrastructure.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from src.evaluation.metrics import EvaluationScores, build_evaluators, result_to_score
from src.evaluation.runner import (
    EvaluationRunResult,
    EvaluationRunner,
    EvaluationSample,
    format_evaluation_report,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def make_sample(
    query: str = "AI/ML internship Python TensorFlow deep learning",
    retrieved_contexts: list[str] | None = None,
    generated_response: str = (
        "Experienced Python developer with TensorFlow skills. "
        "Built a CNN image classifier achieving 92% accuracy."
    ),
    candidate_facts: str = (
        "Name: Test User. Education: BSc Computer Science. "
        "Skills: Python, TensorFlow, PyTorch. "
        "Projects: CNN image classifier, RAG resume generator."
    ),
    job_title: str = "ML Intern",
    company: str = "DeepMind",
) -> EvaluationSample:
    """Build a realistic EvaluationSample with sensible defaults."""
    return EvaluationSample(
        query=query,
        retrieved_contexts=retrieved_contexts or [
            "Use quantifiable metrics in every bullet point.",
            "Tailor keywords closely to the job description.",
            "Highlight relevant academic projects prominently.",
        ],
        generated_response=generated_response,
        candidate_facts=candidate_facts,
        job_title=job_title,
        company=company,
    )


def make_mock_eval_result(score: float, feedback: str = "Mock evaluation feedback.") -> MagicMock:
    """Build a MagicMock that mimics a LlamaIndex EvaluationResult."""
    result = MagicMock()
    result.score = score
    result.passing = score >= 0.5
    result.feedback = feedback
    return result


def make_patched_evaluators(
    faith_score: float = 0.9,
    relevancy_score: float = 0.8,
    precision_score: float = 0.75,
) -> dict:
    """Return a dict of evaluator mocks with fixed scores."""
    return {
        "faithfulness": MagicMock(
            evaluate=MagicMock(return_value=make_mock_eval_result(faith_score, "Claims grounded."))
        ),
        "answer_relevancy": MagicMock(
            evaluate=MagicMock(return_value=make_mock_eval_result(relevancy_score, "Resume is relevant."))
        ),
        "context_precision": MagicMock(
            evaluate=MagicMock(return_value=make_mock_eval_result(precision_score, "Good signal-to-noise."))
        ),
    }


# ---------------------------------------------------------------------------
# EvaluationScores tests
# ---------------------------------------------------------------------------


def test_evaluation_scores_aggregate_perfect() -> None:
    """Geometric mean of three perfect scores should be exactly 1.0."""
    scores = EvaluationScores(faithfulness=1.0, answer_relevancy=1.0, context_precision=1.0)
    assert math.isclose(scores.aggregate_score, 1.0, abs_tol=1e-6)


def test_evaluation_scores_aggregate_geometric_mean() -> None:
    """aggregate_score equals the geometric mean of the three component scores."""
    scores = EvaluationScores(faithfulness=0.8, answer_relevancy=0.6, context_precision=0.9)
    expected = math.pow(0.8 * 0.6 * 0.9, 1.0 / 3.0)
    assert math.isclose(scores.aggregate_score, expected, abs_tol=1e-6)


def test_evaluation_scores_aggregate_penalises_weak_dimension() -> None:
    """Aggregate with one very low score should be lower than the arithmetic mean."""
    scores_weak = EvaluationScores(faithfulness=0.1, answer_relevancy=1.0, context_precision=1.0)
    arithmetic_mean = (0.1 + 1.0 + 1.0) / 3.0
    assert scores_weak.aggregate_score < arithmetic_mean


def test_evaluation_scores_zero_does_not_produce_nan() -> None:
    """Any zero score must produce 0.0, not NaN or a negative number."""
    scores = EvaluationScores(faithfulness=0.0, answer_relevancy=1.0, context_precision=1.0)
    agg = scores.aggregate_score
    assert not math.isnan(agg)
    assert agg == 0.0


def test_evaluation_scores_to_dict_keys_and_types() -> None:
    """to_dict() returns all four expected keys as floats."""
    scores = EvaluationScores(faithfulness=0.8, answer_relevancy=0.6, context_precision=0.9)
    d = scores.to_dict()
    assert set(d.keys()) == {"faithfulness", "answer_relevancy", "context_precision", "aggregate"}
    assert all(isinstance(v, float) for v in d.values())


def test_evaluation_scores_to_dict_values() -> None:
    """to_dict() values match the stored component scores."""
    scores = EvaluationScores(faithfulness=0.75, answer_relevancy=0.80, context_precision=0.65)
    d = scores.to_dict()
    assert d["faithfulness"] == pytest.approx(0.75, abs=1e-4)
    assert d["answer_relevancy"] == pytest.approx(0.80, abs=1e-4)
    assert d["context_precision"] == pytest.approx(0.65, abs=1e-4)
    assert 0.0 <= d["aggregate"] <= 1.0


# ---------------------------------------------------------------------------
# result_to_score tests
# ---------------------------------------------------------------------------


def test_result_to_score_numeric_score() -> None:
    """Numeric score in [0, 1] is returned unchanged."""
    result = MagicMock()
    result.score = 0.75
    assert math.isclose(result_to_score(result), 0.75, abs_tol=1e-9)


def test_result_to_score_clamped_high() -> None:
    """Score above 1.0 is clamped to 1.0."""
    result = MagicMock()
    result.score = 1.5
    assert result_to_score(result) == 1.0


def test_result_to_score_clamped_low() -> None:
    """Negative score is clamped to 0.0."""
    result = MagicMock()
    result.score = -0.3
    assert result_to_score(result) == 0.0


def test_result_to_score_fallback_passing_true() -> None:
    """When score is None and passing=True, returns 1.0."""
    result = MagicMock()
    result.score = None
    result.passing = True
    assert result_to_score(result) == 1.0


def test_result_to_score_fallback_passing_false() -> None:
    """When score is None and passing=False, returns 0.0."""
    result = MagicMock()
    result.score = None
    result.passing = False
    assert result_to_score(result) == 0.0


# ---------------------------------------------------------------------------
# EvaluationSample tests
# ---------------------------------------------------------------------------


def test_evaluation_sample_context_routing() -> None:
    """faithfulness_contexts uses candidate_facts; others use retrieved_contexts."""
    sample = make_sample()
    assert sample.faithfulness_contexts() == [sample.candidate_facts]
    assert sample.relevancy_contexts() == sample.retrieved_contexts
    assert sample.precision_contexts() == sample.retrieved_contexts


def test_evaluation_sample_fields_stored_correctly() -> None:
    """All EvaluationSample fields are stored as provided."""
    sample = make_sample(job_title="Data Intern", company="Google")
    assert sample.job_title == "Data Intern"
    assert sample.company == "Google"
    assert isinstance(sample.retrieved_contexts, list)
    assert len(sample.retrieved_contexts) > 0
    assert isinstance(sample.candidate_facts, str)
    assert len(sample.candidate_facts) > 0


def test_evaluation_sample_faithfulness_context_is_candidate_only() -> None:
    """Faithfulness context must not include retrieved chunks — only profile facts."""
    sample = make_sample(
        candidate_facts="Name: Alice. Skills: Python.",
        retrieved_contexts=["Best practice: use action verbs."],
    )
    faith_ctx = sample.faithfulness_contexts()
    assert faith_ctx == ["Name: Alice. Skills: Python."]
    assert "Best practice" not in faith_ctx[0]


# ---------------------------------------------------------------------------
# build_evaluators tests
# ---------------------------------------------------------------------------


def test_build_evaluators_returns_three_keys() -> None:
    """build_evaluators() returns a dict with the three expected keys."""
    mock_llm = MagicMock()
    evaluators = build_evaluators(mock_llm)
    assert set(evaluators.keys()) == {"faithfulness", "answer_relevancy", "context_precision"}


def test_build_evaluators_objects_are_distinct() -> None:
    """Each value in the returned dict is a distinct evaluator object."""
    mock_llm = MagicMock()
    evaluators = build_evaluators(mock_llm)
    ev_list = list(evaluators.values())
    assert ev_list[0] is not ev_list[1]
    assert ev_list[1] is not ev_list[2]


# ---------------------------------------------------------------------------
# EvaluationRunner tests
# ---------------------------------------------------------------------------


def test_runner_evaluate_sample_success() -> None:
    """Runner populates EvaluationScores correctly from mocked evaluators."""
    runner = EvaluationRunner(llm=MagicMock())

    with patch.object(runner, "_get_evaluators", return_value=make_patched_evaluators(0.9, 0.8, 0.7)):
        result = runner.evaluate_sample(make_sample())

    assert result.success
    assert result.error is None
    assert math.isclose(result.scores.faithfulness, 0.9, abs_tol=1e-6)
    assert math.isclose(result.scores.answer_relevancy, 0.8, abs_tol=1e-6)
    assert math.isclose(result.scores.context_precision, 0.7, abs_tol=1e-6)
    assert result.scores.aggregate_score > 0.0


def test_runner_evaluate_sample_feedback_captured() -> None:
    """Evaluator feedback strings are stored in the scores object."""
    runner = EvaluationRunner(llm=MagicMock())

    with patch.object(runner, "_get_evaluators", return_value=make_patched_evaluators()):
        result = runner.evaluate_sample(make_sample())

    assert "faithfulness" in result.scores.feedback
    assert "answer_relevancy" in result.scores.feedback
    assert "context_precision" in result.scores.feedback


def test_runner_evaluate_sample_on_faithfulness_error() -> None:
    """Evaluator exception produces zero scores, success=False, and error message."""
    runner = EvaluationRunner(llm=MagicMock())

    failing_evaluators = make_patched_evaluators()
    failing_evaluators["faithfulness"].evaluate.side_effect = RuntimeError("LLM quota exceeded")

    with patch.object(runner, "_get_evaluators", return_value=failing_evaluators):
        result = runner.evaluate_sample(make_sample())

    assert not result.success
    assert result.error is not None
    assert "quota" in result.error.lower()
    assert result.scores.faithfulness == 0.0
    assert result.scores.answer_relevancy == 0.0
    assert result.scores.context_precision == 0.0


def test_runner_evaluate_batch_returns_all_results() -> None:
    """evaluate_batch processes every sample and returns matching count."""
    runner = EvaluationRunner(llm=MagicMock())

    with patch.object(runner, "_get_evaluators", return_value=make_patched_evaluators()):
        samples = [make_sample(company=f"Co{i}") for i in range(4)]
        results = runner.evaluate_batch(samples)

    assert len(results) == 4
    assert all(r.success for r in results)


def test_runner_evaluate_batch_individual_failures_do_not_abort() -> None:
    """A failing sample in a batch does not prevent others from being evaluated."""
    runner = EvaluationRunner(llm=MagicMock())

    call_count = 0

    def evaluate_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise RuntimeError("Simulated LLM failure")
        return make_mock_eval_result(0.8)

    patched = make_patched_evaluators()
    for key in patched:
        patched[key].evaluate.side_effect = evaluate_side_effect

    with patch.object(runner, "_get_evaluators", return_value=patched):
        results = runner.evaluate_batch([make_sample(company=f"Co{i}") for i in range(3)])

    # All 3 results returned regardless of the failure in the middle.
    assert len(results) == 3


def test_runner_evaluators_built_lazily() -> None:
    """Evaluators are not built until _get_evaluators() is called."""
    runner = EvaluationRunner(llm=MagicMock())
    assert runner._evaluators is None
    _ = runner._get_evaluators()
    assert runner._evaluators is not None


def test_runner_evaluators_cached_across_calls() -> None:
    """_get_evaluators() returns the same dict object on repeated calls."""
    runner = EvaluationRunner(llm=MagicMock())
    ev1 = runner._get_evaluators()
    ev2 = runner._get_evaluators()
    assert ev1 is ev2


# ---------------------------------------------------------------------------
# format_evaluation_report tests
# ---------------------------------------------------------------------------


def test_format_evaluation_report_empty_input() -> None:
    """Empty results list produces a warning report without crashing."""
    report = format_evaluation_report([])
    assert "No evaluation samples" in report


def test_format_evaluation_report_contains_header() -> None:
    """Report starts with the expected Markdown H1 header."""
    scores = EvaluationScores(faithfulness=0.9, answer_relevancy=0.8, context_precision=0.75)
    result = EvaluationRunResult(sample=make_sample(), scores=scores)
    report = format_evaluation_report([result])
    assert "# 📊 RAG Pipeline Evaluation Report" in report


def test_format_evaluation_report_contains_all_metric_columns() -> None:
    """Report table headers include all three metric names plus aggregate."""
    scores = EvaluationScores(faithfulness=0.9, answer_relevancy=0.8, context_precision=0.75)
    result = EvaluationRunResult(sample=make_sample(), scores=scores)
    report = format_evaluation_report([result])
    assert "Faithfulness" in report
    assert "Answer Relevancy" in report
    assert "Context Precision" in report
    assert "Aggregate" in report


def test_format_evaluation_report_sample_data_present() -> None:
    """Job title and company appear in the report table rows."""
    scores = EvaluationScores(faithfulness=0.9, answer_relevancy=0.8, context_precision=0.75)
    result = EvaluationRunResult(sample=make_sample(job_title="ML Intern", company="DeepMind"), scores=scores)
    report = format_evaluation_report([result])
    assert "ML Intern" in report
    assert "DeepMind" in report


def test_format_evaluation_report_failure_section() -> None:
    """Failed evaluations appear in a dedicated Failures section."""
    scores = EvaluationScores(faithfulness=0.0, answer_relevancy=0.0, context_precision=0.0)
    failed = EvaluationRunResult(sample=make_sample(), scores=scores, error="API timeout after 30s")
    report = format_evaluation_report([failed])
    assert "Failures" in report
    assert "API timeout after 30s" in report


def test_format_evaluation_report_averages_for_multiple_samples() -> None:
    """Report includes an averages line when there are multiple successful samples."""
    results = []
    for faith, rel, prec in [(0.9, 0.8, 0.7), (0.8, 0.7, 0.9)]:
        scores = EvaluationScores(faithfulness=faith, answer_relevancy=rel, context_precision=prec)
        results.append(EvaluationRunResult(sample=make_sample(), scores=scores))
    report = format_evaluation_report(results)
    assert "Averages" in report


def test_format_evaluation_report_metric_definitions_present() -> None:
    """Report includes the metric definitions table."""
    scores = EvaluationScores(faithfulness=1.0, answer_relevancy=1.0, context_precision=1.0)
    result = EvaluationRunResult(sample=make_sample(), scores=scores)
    report = format_evaluation_report([result])
    assert "Metric Definitions" in report
    assert "RAGAS Parallel" in report
    assert "ADR-009" in report
