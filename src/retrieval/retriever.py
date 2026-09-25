"""Hybrid retrieval module combining dense vector search and BM25 sparse search."""

from __future__ import annotations

import logging
from typing import Any

from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import BaseNode, NodeWithScore, QueryBundle
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.retrievers.bm25 import BM25Retriever

from src.data.job_posting import JobPosting

logger = logging.getLogger(__name__)


def reciprocal_rank_fusion(
    results_list: list[list[NodeWithScore]],
    k: int = 60,
    top_k: int = 5,
) -> list[NodeWithScore]:
    """Fuse and rerank retrieved nodes from multiple search sources using RRF.

    Reciprocal Rank Fusion computes a composite score:
        RRF_score(d) = sum(1 / (k + rank_i(d)))
    for each result list i, producing an unbiased, calibrated hybrid ranking.

    Args:
        results_list: List of ranked node lists from different retrievers.
        k: Constant ranking penalty factor (default 60).
        top_k: Number of top fused nodes to return.

    Returns:
        list[NodeWithScore]: Reranked, deduplicated list of nodes with RRF scores.
    """
    node_map: dict[str, BaseNode] = {}
    rrf_scores: dict[str, float] = {}

    for results in results_list:
        for rank, node_with_score in enumerate(results, start=1):
            node_id = node_with_score.node.node_id
            node_map[node_id] = node_with_score.node
            rrf_scores[node_id] = rrf_scores.get(node_id, 0.0) + (1.0 / (k + rank))

    sorted_node_ids = sorted(
        rrf_scores.keys(),
        key=lambda nid: rrf_scores[nid],
        reverse=True,
    )[:top_k]

    return [
        NodeWithScore(node=node_map[nid], score=rrf_scores[nid])
        for nid in sorted_node_ids
    ]


def format_retrieved_context(nodes: list[NodeWithScore]) -> str:
    """Format retrieved nodes into a clean structured string for LLM prompt injection.

    Args:
        nodes: List of retrieved nodes with relevance scores.

    Returns:
        str: Formatted markdown-style context block.
    """
    if not nodes:
        return ""

    sections = []
    for i, item in enumerate(nodes, start=1):
        meta = item.node.metadata or {}
        category = meta.get("category", "General")
        topic = meta.get("topic", "Best Practice")
        text = item.node.get_content().strip()

        score_info = f" (relevance: {item.score:.3f})" if item.score is not None else ""
        section = (
            f"### [Guideline {i}: {topic} | Category: {category}]{score_info}\n"
            f"{text}"
        )
        sections.append(section)

    return "\n\n".join(sections)


class HybridResumeRetriever:
    """Hybrid search retriever combining ChromaDB dense vectors and BM25 sparse search.

    Uses Reciprocal Rank Fusion (RRF) to merge and deduplicate results,
    supporting metadata filtering by knowledge base category.

    Attributes:
        index: VectorStoreIndex backed by ChromaDB.
        nodes: Optional list of BaseNodes used for BM25 sparse indexing.
        similarity_top_k: Number of candidates retrieved from dense vector search.
        bm25_top_k: Number of candidates retrieved from BM25 sparse search.
    """

    def __init__(
        self,
        index: VectorStoreIndex,
        nodes: list[BaseNode] | None = None,
        similarity_top_k: int = 5,
        bm25_top_k: int = 5,
    ) -> None:
        """Initialize HybridResumeRetriever.

        Args:
            index: VectorStoreIndex configured with ChromaDB vector store.
            nodes: Optional list of nodes to build BM25 sparse retriever.
            similarity_top_k: Dense vector search candidate pool size.
            bm25_top_k: BM25 search candidate pool size.
        """
        self.index = index
        self.nodes = nodes
        self.similarity_top_k = similarity_top_k
        self.bm25_top_k = bm25_top_k

        self._bm25_retriever: BM25Retriever | None = None
        if nodes:
            try:
                self._bm25_retriever = BM25Retriever.from_defaults(
                    nodes=nodes,
                    similarity_top_k=bm25_top_k,
                )
                logger.info("Initialized BM25 sparse retriever with %d nodes.", len(nodes))
            except Exception as e:
                logger.warning("Could not initialize BM25Retriever: %s", e)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[NodeWithScore]:
        """Perform hybrid retrieval for a query string.

        Runs dense vector search on the ChromaDB index and sparse BM25 search
        on indexed nodes, then combines rankings via Reciprocal Rank Fusion.

        Args:
            query: Search query text.
            top_k: Number of top results to return.
            category: Optional category filter (e.g. 'resume_best_practices').

        Returns:
            list[NodeWithScore]: Reranked and deduplicated nodes with RRF scores.
        """
        query_bundle = QueryBundle(query_str=query)
        retriever_results: list[list[NodeWithScore]] = []

        # 1. Dense Vector Retrieval (ChromaDB)
        filters = None
        if category:
            filters = MetadataFilters(
                filters=[ExactMatchFilter(key="category", value=category)]
            )

        vector_retriever = VectorIndexRetriever(
            index=self.index,
            similarity_top_k=self.similarity_top_k,
            filters=filters,
        )

        try:
            dense_results = vector_retriever.retrieve(query_bundle)
            retriever_results.append(dense_results)
            logger.debug("Dense retrieval returned %d nodes.", len(dense_results))
        except Exception as e:
            logger.error("Dense vector retrieval failed: %s", e)

        # 2. Sparse BM25 Retrieval (if available)
        if self._bm25_retriever is not None:
            try:
                bm25_results = self._bm25_retriever.retrieve(query_bundle)
                # If category filter specified, filter BM25 results in memory
                if category:
                    bm25_results = [
                        res for res in bm25_results
                        if res.node.metadata.get("category") == category
                    ]
                retriever_results.append(bm25_results)
                logger.debug("BM25 retrieval returned %d nodes.", len(bm25_results))
            except Exception as e:
                logger.warning("BM25 retrieval failed: %s", e)

        # 3. Fuse results via Reciprocal Rank Fusion
        if not retriever_results or all(len(r) == 0 for r in retriever_results):
            logger.warning("No nodes retrieved for query: '%s'", query[:60])
            return []

        if len(retriever_results) == 1:
            return retriever_results[0][:top_k]

        fused_nodes = reciprocal_rank_fusion(
            results_list=retriever_results,
            k=60,
            top_k=top_k,
        )

        logger.info(
            "Hybrid retrieval returned %d nodes for query: '%s'",
            len(fused_nodes),
            query[:60],
        )
        return fused_nodes

    def retrieve_for_job(
        self,
        job: JobPosting,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[NodeWithScore]:
        """Retrieve relevant knowledge base chunks for an internship job posting.

        Extracts the semantic search query via job.to_search_query() and executes
        the hybrid retrieval pipeline.

        Args:
            job: JobPosting instance containing job requirements and tech stack.
            top_k: Number of final recommendations to return.
            category: Optional category filter ('resume_best_practices', 'hr_recruitment').

        Returns:
            list[NodeWithScore]: Retrieved advice and guideline chunks.
        """
        query = job.to_search_query()
        return self.retrieve(query=query, top_k=top_k, category=category)
