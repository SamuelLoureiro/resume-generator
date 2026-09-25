"""Evaluation metrics for the RAG resume generation pipeline.

Implements three quality dimensions aligned with RAGAS methodology using
LlamaIndex's native evaluation framework and the project's Gemini LLM as
the evaluation judge.

Metric mapping (LlamaIndex → RAGAS equivalent):

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - LlamaIndex Evaluator
     - RAGAS Metric
     - What it measures in this project
   * - ``FaithfulnessEvaluator``
     - ``faithfulness``
     - Are all resume claims grounded in the candidate profile?
   * - ``RelevancyEvaluator``
     - ``answer_relevancy``
     - Is the resume relevant to the target job?
   * - ``ContextRelevancyEvaluator``
     - ``context_precision``
     - Are the retrieved KB chunks useful for this job?

Note:
    RAGAS 0.4.x cannot be imported when ``langchain-community >= 0.3.x``
    is installed (``langchain_community.chat_models.vertexai`` was removed).
    See ADR-009 in ``docs/decisions_log.md`` for the full rationale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from llama_index.core.evaluation import (
    ContextRelevancyEvaluator,
    EvaluationResult,
    FaithfulnessEvaluator,
    RelevancyEvaluator,
)
from llama_index.core.llms import LLM


@dataclass
class EvaluationScores:
    """Aggregated quality scores for a single resume generation run.

    Attributes:
        faithfulness: Fraction of resume claims grounded in the candidate
            profile. 0.0 = all hallucinated, 1.0 = fully faithful.
        answer_relevancy: Relevance of the generated resume to the job
            description. 0.0 = irrelevant, 1.0 = highly relevant.
        context_precision: Signal-to-noise ratio of the retrieved knowledge
            base chunks. 0.0 = all noise, 1.0 = all signal.
        feedback: Dict mapping metric name to the evaluator's reasoning text.
    """

    faithfulness: float
    answer_relevancy: float
    context_precision: float
    feedback: dict[str, str] = field(default_factory=dict)

    @property
    def aggregate_score(self) -> float:
        """Geometric mean of all three scores in the [0, 1] range.

        The geometric mean strongly penalises extreme weakness in any single
        dimension, encouraging balanced quality across all three axes.
        """
        product = self.faithfulness * self.answer_relevancy * self.context_precision
        # Guard against zero/negative products to avoid domain errors.
        return math.pow(max(product, 1e-9), 1.0 / 3.0) if product > 0 else 0.0

    def to_dict(self) -> dict[str, float]:
        """Return a flat mapping of metric names to rounded scores.

        Returns:
            dict with keys: faithfulness, answer_relevancy,
            context_precision, aggregate.
        """
        return {
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevancy": round(self.answer_relevancy, 4),
            "context_precision": round(self.context_precision, 4),
            "aggregate": round(self.aggregate_score, 4),
        }


def build_evaluators(
    llm: LLM,
) -> dict[str, FaithfulnessEvaluator | RelevancyEvaluator | ContextRelevancyEvaluator]:
    """Build the three configured LlamaIndex evaluators.

    Args:
        llm: A LlamaIndex-compatible LLM instance. In production, use
            Gemini 2.5 Flash/Pro. In unit tests, use ``MockLLM`` to
            avoid real API calls.

    Returns:
        Dict with keys ``'faithfulness'``, ``'answer_relevancy'``,
        ``'context_precision'`` mapping to their evaluator instances.
    """
    return {
        "faithfulness": FaithfulnessEvaluator(llm=llm),
        "answer_relevancy": RelevancyEvaluator(llm=llm),
        "context_precision": ContextRelevancyEvaluator(llm=llm),
    }


def result_to_score(result: EvaluationResult) -> float:
    """Extract a normalised 0–1 float score from a LlamaIndex EvaluationResult.

    LlamaIndex evaluators may return a continuous ``score`` or only a binary
    ``passing`` flag. This helper normalises both cases to ``[0.0, 1.0]``.

    Args:
        result: Evaluation result from a LlamaIndex evaluator.

    Returns:
        Clamped score in [0.0, 1.0]. Returns 1.0/0.0 from ``passing`` when
        ``score`` is ``None``.
    """
    if result.score is not None:
        return float(max(0.0, min(1.0, result.score)))
    # Fall back to binary passing flag when no numeric score is available.
    return 1.0 if result.passing else 0.0
