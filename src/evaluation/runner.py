"""End-to-end evaluation runner for the RAG resume generation pipeline.

Orchestrates the three RAGAS-aligned evaluators over one or more
``EvaluationSample`` data points and produces a structured Markdown report.

Usage example (production)::

    from llama_index.core.llms import Gemini
    from src.evaluation.runner import EvaluationRunner, EvaluationSample

    runner = EvaluationRunner(llm=get_gemini_llm())
    sample = EvaluationSample(
        query="ML internship Python PyTorch computer vision",
        retrieved_contexts=["...chunk 1...", "...chunk 2..."],
        generated_response="Generated resume text...",
        candidate_facts="Name: Alice. Education: BSc CS. Skills: Python, PyTorch.",
        job_title="ML Intern",
        company="DeepMind",
    )
    result = runner.evaluate_sample(sample)
    print(result.scores.to_dict())

Usage example (offline / tests)::

    from unittest.mock import MagicMock, patch
    runner = EvaluationRunner(llm=MagicMock())
    with patch.object(runner, "_get_evaluators", return_value={...}):
        result = runner.evaluate_sample(sample)
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from llama_index.core.llms import LLM

from src.evaluation.metrics import EvaluationScores, build_evaluators, result_to_score

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EvaluationSample:
    """Single data point for evaluating one resume generation run.

    Attributes:
        query: Semantic search query derived from the job posting via
            ``JobPosting.to_search_query()``.  Used as the "question" for
            all three evaluators.
        retrieved_contexts: Text content of chunks retrieved from the
            knowledge base by the hybrid retriever. Used for answer relevancy
            and context precision evaluation.
        generated_response: Generated resume content as a plain-text string
            (the "answer").  All three evaluators receive this.
        candidate_facts: Concatenated candidate profile fields in prose form.
            Used exclusively as the **faithfulness reference context** —
            i.e., the ground truth of what may legitimately appear in the
            resume.  Must never include fabricated information.
        job_title: Human-readable job title for report display.
        company: Target company name for report display.
    """

    query: str
    retrieved_contexts: list[str]
    generated_response: str
    candidate_facts: str
    job_title: str = ""
    company: str = ""

    # ------------------------------------------------------------------
    # Context routing helpers
    # ------------------------------------------------------------------

    def faithfulness_contexts(self) -> list[str]:
        """Return reference contexts for faithfulness evaluation.

        Returns:
            Singleton list containing ``candidate_facts`` — the only
            legitimate source of information for the generated resume.
        """
        return [self.candidate_facts]

    def relevancy_contexts(self) -> list[str]:
        """Return contexts for answer relevancy evaluation.

        Returns:
            Retrieved knowledge-base chunks (the "retrieval context").
        """
        return self.retrieved_contexts

    def precision_contexts(self) -> list[str]:
        """Return contexts for context precision evaluation.

        Returns:
            Retrieved knowledge-base chunks to be judged for relevance.
        """
        return self.retrieved_contexts


@dataclass
class EvaluationRunResult:
    """Outcome of evaluating a single ``EvaluationSample``.

    Attributes:
        sample: The input data point that was evaluated.
        scores: The computed metric scores.
        error: Error message if evaluation failed; ``None`` on success.
    """

    sample: EvaluationSample
    scores: EvaluationScores
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        """True when no error occurred during evaluation."""
        return self.error is None


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


class EvaluationRunner:
    """Orchestrates quality evaluation of the RAG resume generation pipeline.

    Runs three LlamaIndex evaluators mirroring RAGAS metrics:

    * ``FaithfulnessEvaluator`` — anti-hallucination
    * ``RelevancyEvaluator`` — answer relevancy
    * ``ContextRelevancyEvaluator`` — context precision

    Evaluators are built lazily on first use to avoid unnecessary
    LLM initialisation during test collection.

    Args:
        llm: LlamaIndex-compatible LLM used as the evaluation judge.
            In production, use Gemini 2.5 Flash/Pro via
            ``src.generation.chain.get_gemini_llm()``.
            In unit tests, use ``MagicMock()`` and patch
            ``_get_evaluators()`` to avoid real API calls.

    Example::

        >>> from llama_index.core.llms import MockLLM
        >>> runner = EvaluationRunner(llm=MockLLM())
        >>> result = runner.evaluate_sample(sample)
        >>> print(result.scores.aggregate_score)
    """

    def __init__(self, llm: LLM) -> None:
        self._llm = llm
        self._evaluators: dict | None = None

    def _get_evaluators(self) -> dict:
        """Lazily build and cache evaluators on first call.

        Returns:
            Dict with keys ``'faithfulness'``, ``'answer_relevancy'``,
            ``'context_precision'``.
        """
        if self._evaluators is None:
            self._evaluators = build_evaluators(self._llm)
        return self._evaluators

    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationRunResult:
        """Run all three metrics on a single ``EvaluationSample``.

        Calls each evaluator with the appropriate context routing defined by
        the sample's helper methods:

        * **Faithfulness**: contexts = ``[candidate_facts]``
        * **Answer Relevancy**: contexts = ``retrieved_contexts``
        * **Context Precision**: contexts = ``retrieved_contexts``

        Args:
            sample: The data point to evaluate.

        Returns:
            ``EvaluationRunResult`` with populated ``scores`` on success, or
            zero scores and a non-``None`` ``error`` message on failure.
        """
        evaluators = self._get_evaluators()
        tag = f"'{sample.job_title} @ {sample.company}'"

        try:
            logger.info("Evaluating faithfulness for sample %s", tag)
            faith_result = evaluators["faithfulness"].evaluate(
                query=sample.query,
                response=sample.generated_response,
                contexts=sample.faithfulness_contexts(),
            )

            logger.info("Evaluating answer relevancy for sample %s", tag)
            relevancy_result = evaluators["answer_relevancy"].evaluate(
                query=sample.query,
                response=sample.generated_response,
                contexts=sample.relevancy_contexts(),
            )

            logger.info("Evaluating context precision for sample %s", tag)
            precision_result = evaluators["context_precision"].evaluate(
                query=sample.query,
                response=sample.generated_response,
                contexts=sample.precision_contexts(),
            )

            scores = EvaluationScores(
                faithfulness=result_to_score(faith_result),
                answer_relevancy=result_to_score(relevancy_result),
                context_precision=result_to_score(precision_result),
                feedback={
                    "faithfulness": faith_result.feedback or "",
                    "answer_relevancy": relevancy_result.feedback or "",
                    "context_precision": precision_result.feedback or "",
                },
            )
            logger.info(
                "Evaluation complete for %s — aggregate=%.3f",
                tag,
                scores.aggregate_score,
            )
            return EvaluationRunResult(sample=sample, scores=scores)

        except Exception as exc:
            logger.error(
                "Evaluation failed for sample %s: %s", tag, exc, exc_info=True
            )
            return EvaluationRunResult(
                sample=sample,
                scores=EvaluationScores(
                    faithfulness=0.0,
                    answer_relevancy=0.0,
                    context_precision=0.0,
                ),
                error=str(exc),
            )

    def evaluate_batch(
        self, samples: list[EvaluationSample]
    ) -> list[EvaluationRunResult]:
        """Run evaluation over a list of samples sequentially.

        Args:
            samples: Data points to evaluate.

        Returns:
            List of ``EvaluationRunResult`` in the same order as input.
            Individual failures do not abort the batch.
        """
        logger.info("Starting batch evaluation: %d samples", len(samples))
        return [self.evaluate_sample(s) for s in samples]


# ---------------------------------------------------------------------------
# Report formatter
# ---------------------------------------------------------------------------


def format_evaluation_report(results: list[EvaluationRunResult]) -> str:
    """Generate a Markdown evaluation report from a list of run results.

    Args:
        results: Evaluation outcomes produced by ``EvaluationRunner``.

    Returns:
        Formatted Markdown string suitable for ``docs/evaluation.md`` or
        console display.
    """
    if not results:
        return (
            "## ⚠️ Evaluation Report\n\n"
            "No evaluation samples provided.\n"
        )

    successful = [r for r in results if r.success]
    failed = [r for r in results if not r.success]

    lines: list[str] = [
        "# 📊 RAG Pipeline Evaluation Report",
        "",
        f"**Samples evaluated:** {len(results)}  ",
        f"**Successful:** {len(successful)}  ",
        f"**Failed:** {len(failed)}",
        "",
        "---",
        "",
        "## Metric Scores",
        "",
        "| # | Job Title | Company | Faithfulness ↑ | Answer Relevancy ↑ | Context Precision ↑ | Aggregate ↑ |",
        "|---|-----------|---------|:--------------:|:------------------:|:-------------------:|:-----------:|",
    ]

    for idx, result in enumerate(results, start=1):
        s = result.scores
        status = "✅" if result.success else "❌"
        lines.append(
            f"| {idx} "
            f"| {result.sample.job_title or '—'} "
            f"| {result.sample.company or '—'} "
            f"| {s.faithfulness:.3f} "
            f"| {s.answer_relevancy:.3f} "
            f"| {s.context_precision:.3f} "
            f"| {s.aggregate_score:.3f} {status} |"
        )

    # Averages row (successful samples only).
    if successful:
        avg_faith = sum(r.scores.faithfulness for r in successful) / len(successful)
        avg_rel = sum(r.scores.answer_relevancy for r in successful) / len(successful)
        avg_prec = sum(r.scores.context_precision for r in successful) / len(successful)
        product = avg_faith * avg_rel * avg_prec
        avg_agg = math.pow(max(product, 1e-9), 1.0 / 3.0) if product > 0 else 0.0

        lines += [
            "",
            f"> **Averages (n={len(successful)}):** "
            f"Faithfulness `{avg_faith:.3f}` | "
            f"Answer Relevancy `{avg_rel:.3f}` | "
            f"Context Precision `{avg_prec:.3f}` | "
            f"Aggregate `{avg_agg:.3f}`",
        ]

    # Failure details.
    if failed:
        lines += [
            "",
            "## ⚠️ Failures",
            "",
        ]
        for result in failed:
            lines.append(
                f"- **{result.sample.job_title} @ {result.sample.company}**: "
                f"`{result.error}`"
            )

    # Metric definitions.
    lines += [
        "",
        "---",
        "",
        "## Metric Definitions",
        "",
        "| Metric | RAGAS Parallel | Definition |",
        "|--------|---------------|-----------|",
        "| **Faithfulness** | `faithfulness` | Fraction of resume claims grounded in the verified candidate profile. Score 1.0 = zero hallucination. |",
        "| **Answer Relevancy** | `answer_relevancy` | Degree to which the generated resume is relevant for the target job description. |",
        "| **Context Precision** | `context_precision` | Signal-to-noise ratio of the knowledge-base chunks retrieved by the hybrid retriever. |",
        "| **Aggregate** | — | Geometric mean of the three scores. Penalises extreme weakness in any single dimension. |",
        "",
        "> *Evaluator backend: LlamaIndex native evaluators (Gemini judge LLM).*  ",
        "> *See ADR-009 in `docs/decisions_log.md` for rationale.*",
    ]

    return "\n".join(lines) + "\n"
