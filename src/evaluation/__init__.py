"""Evaluation sub-package for assessing RAG pipeline output quality.

Provides three RAGAS-aligned quality metrics implemented via LlamaIndex's
native evaluation framework and the project's existing Gemini LLM:

Metrics (parallel to RAGAS definitions):
    - **Faithfulness** (anti-hallucination): every claim in the generated
      resume must be grounded in the verified candidate profile.
    - **Answer Relevancy**: the generated resume must be relevant and
      appropriate for the target job description.
    - **Context Precision**: the knowledge-base chunks retrieved by the
      hybrid retriever must carry useful, on-topic signal.

Note:
    RAGAS 0.4.x is incompatible with ``langchain-community >= 0.3.x``
    (see ADR-009 in ``docs/decisions_log.md``). LlamaIndex evaluators
    are used instead; they measure the same dimensions with the same 0-1
    scoring convention.
"""

from src.evaluation.metrics import EvaluationScores, build_evaluators, result_to_score
from src.evaluation.runner import (
    EvaluationRunResult,
    EvaluationRunner,
    EvaluationSample,
    format_evaluation_report,
)

__all__ = [
    "EvaluationScores",
    "EvaluationRunResult",
    "EvaluationRunner",
    "EvaluationSample",
    "build_evaluators",
    "format_evaluation_report",
    "result_to_score",
]
