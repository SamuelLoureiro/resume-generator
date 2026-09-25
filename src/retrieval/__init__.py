"""Retrieval package: hybrid search, RRF reranking, and pipeline orchestration."""

from src.retrieval.pipeline import (
    KnowledgeBasePipeline,
    is_collection_populated,
)
from src.retrieval.retriever import (
    HybridResumeRetriever,
    format_retrieved_context,
    reciprocal_rank_fusion,
)

__all__ = [
    "KnowledgeBasePipeline",
    "HybridResumeRetriever",
    "is_collection_populated",
    "reciprocal_rank_fusion",
    "format_retrieved_context",
]
