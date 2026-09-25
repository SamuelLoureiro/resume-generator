"""Unit and integration tests for HybridResumeRetriever using MockEmbedding (100% offline)."""

from __future__ import annotations

from pathlib import Path
import pytest
from llama_index.core import Document
from llama_index.core.embeddings.mock_embed_model import MockEmbedding
from llama_index.core.schema import NodeWithScore, TextNode

from src.data.job_posting import JobPosting
from src.ingestion.indexer import (
    KnowledgeBaseIndexer,
    build_sentence_splitter,
)
from src.ingestion.loader import KnowledgeBaseLoader
from src.retrieval.retriever import (
    HybridResumeRetriever,
    format_retrieved_context,
    reciprocal_rank_fusion,
)


# ---------------------------------------------------------------------------
# Fixtures / Helpers
# ---------------------------------------------------------------------------

def make_sample_nodes() -> list[TextNode]:
    """Create sample nodes with metadata for testing retrieval."""
    return [
        TextNode(
            text="Use the XYZ formula to quantify your engineering achievements on resumes.",
            metadata={"category": "resume_best_practices", "topic": "XYZ Formula"},
            id_="node_1",
        ),
        TextNode(
            text="ATS systems like Workday and Greenhouse parse linear formatting and keywords.",
            metadata={"category": "resume_best_practices", "topic": "ATS Optimization"},
            id_="node_2",
        ),
        TextNode(
            text="Recruiters look for strong computer science fundamentals and learning agility in interns.",
            metadata={"category": "hr_recruitment", "topic": "Recruiter Expectations"},
            id_="node_3",
        ),
        TextNode(
            text="Big Tech values algorithms, data structures, and clean architecture with pytest.",
            metadata={"category": "hr_recruitment", "topic": "Big Tech Recruitment"},
            id_="node_4",
        ),
    ]


def build_test_index(nodes: list[TextNode], tmp_path: Path):
    """Build a VectorStoreIndex from nodes using MockEmbedding."""
    embed_model = MockEmbedding(embed_dim=768)
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=tmp_path / "chroma_retrieval_test",
        collection_name="test_retrieval",
    )
    docs = [
        Document(text=n.text, metadata=n.metadata, id_=n.node_id)
        for n in nodes
    ]
    index = indexer.build_index(docs)
    return index


# ---------------------------------------------------------------------------
# Reciprocal Rank Fusion tests
# ---------------------------------------------------------------------------

def test_reciprocal_rank_fusion_merges_and_deduplicates() -> None:
    """Test that RRF combines two ranked lists and correctly sums ranks."""
    n1 = TextNode(text="Node 1 text", id_="id_1")
    n2 = TextNode(text="Node 2 text", id_="id_2")
    n3 = TextNode(text="Node 3 text", id_="id_3")

    # List 1: id_1 (rank 1), id_2 (rank 2)
    list1 = [NodeWithScore(node=n1, score=0.9), NodeWithScore(node=n2, score=0.8)]
    # List 2: id_2 (rank 1), id_3 (rank 2)
    list2 = [NodeWithScore(node=n2, score=0.95), NodeWithScore(node=n3, score=0.7)]

    fused = reciprocal_rank_fusion([list1, list2], k=60, top_k=3)

    # id_2 appears in both lists (rank 2 in list1, rank 1 in list2)
    # id_2 score = 1/(60+2) + 1/(60+1) ~ 0.0161 + 0.0164 = 0.0325 -> highest score!
    assert len(fused) == 3
    assert fused[0].node.node_id == "id_2"
    assert fused[0].score > fused[1].score


def test_reciprocal_rank_fusion_empty_lists() -> None:
    """Test that RRF handles empty result lists gracefully."""
    fused = reciprocal_rank_fusion([], top_k=5)
    assert fused == []

    fused2 = reciprocal_rank_fusion([[], []], top_k=5)
    assert fused2 == []


# ---------------------------------------------------------------------------
# format_retrieved_context tests
# ---------------------------------------------------------------------------

def test_format_retrieved_context_output() -> None:
    """Test that format_retrieved_context formats nodes with category and topic."""
    nodes = make_sample_nodes()[:2]
    scored = [
        NodeWithScore(node=nodes[0], score=0.032),
        NodeWithScore(node=nodes[1], score=0.016),
    ]

    context = format_retrieved_context(scored)

    assert "### [Guideline 1: XYZ Formula | Category: resume_best_practices]" in context
    assert "Use the XYZ formula" in context
    assert "### [Guideline 2: ATS Optimization | Category: resume_best_practices]" in context
    assert "relevance: 0.032" in context


def test_format_retrieved_context_empty() -> None:
    """Test that format_retrieved_context returns empty string on empty input."""
    assert format_retrieved_context([]) == ""


# ---------------------------------------------------------------------------
# HybridResumeRetriever tests
# ---------------------------------------------------------------------------

def test_hybrid_retriever_dense_only(tmp_path: Path) -> None:
    """Test HybridResumeRetriever works with only dense vector index (no BM25 nodes)."""
    nodes = make_sample_nodes()
    index = build_test_index(nodes, tmp_path)

    retriever = HybridResumeRetriever(index=index, nodes=None, similarity_top_k=2)
    results = retriever.retrieve("quantify engineering achievements", top_k=2)

    assert len(results) <= 2
    assert all(isinstance(r, NodeWithScore) for r in results)


def test_hybrid_retriever_with_bm25(tmp_path: Path) -> None:
    """Test HybridResumeRetriever combines vector search and BM25 exact matching."""
    nodes = make_sample_nodes()
    index = build_test_index(nodes, tmp_path)

    retriever = HybridResumeRetriever(
        index=index,
        nodes=nodes,
        similarity_top_k=3,
        bm25_top_k=3,
    )

    # Query with exact keyword from node_4 ("pytest")
    results = retriever.retrieve("clean architecture with pytest", top_k=3)

    assert len(results) > 0
    # Top result should mention pytest or clean architecture
    top_texts = [r.node.get_content() for r in results]
    assert any("pytest" in t for t in top_texts)


def test_hybrid_retriever_category_filtering(tmp_path: Path) -> None:
    """Test that category filtering restricts results to the target category."""
    nodes = make_sample_nodes()
    index = build_test_index(nodes, tmp_path)

    retriever = HybridResumeRetriever(
        index=index,
        nodes=nodes,
        similarity_top_k=4,
        bm25_top_k=4,
    )

    # Filter by hr_recruitment only
    results = retriever.retrieve(
        query="resume formatting",
        top_k=4,
        category="hr_recruitment",
    )

    for r in results:
        assert r.node.metadata.get("category") == "hr_recruitment"


def test_hybrid_retriever_retrieve_for_job(tmp_path: Path) -> None:
    """Test retrieving advice directly from a JobPosting instance."""
    nodes = make_sample_nodes()
    index = build_test_index(nodes, tmp_path)

    retriever = HybridResumeRetriever(
        index=index,
        nodes=nodes,
        similarity_top_k=3,
        bm25_top_k=3,
    )

    job = JobPosting(
        title="Software Engineering Intern",
        company="Big Tech Corp",
        raw_description="Looking for an intern with clean code, testing, and algorithmic skills.",
        technologies=["Python", "pytest", "Docker"],
        requirements=["Knowledge of algorithms and data structures"],
    )

    results = retriever.retrieve_for_job(job=job, top_k=2)

    assert len(results) <= 2
    assert len(results) > 0


def test_hybrid_retriever_end_to_end_with_real_kb(tmp_path: Path) -> None:
    """End-to-end integration test using real knowledge base documents."""
    loader = KnowledgeBaseLoader()
    docs = loader.load_all_documents()
    assert len(docs) >= 10

    # Split docs into nodes
    splitter = build_sentence_splitter()
    nodes = splitter.get_nodes_from_documents(docs)
    assert len(nodes) >= 10

    # Build index with MockEmbedding
    embed_model = MockEmbedding(embed_dim=768)
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=tmp_path / "real_kb_retrieval",
        collection_name="real_kb_retrieval",
    )
    index = indexer.build_index(docs)

    # Create hybrid retriever
    retriever = HybridResumeRetriever(
        index=index,
        nodes=nodes,
        similarity_top_k=5,
        bm25_top_k=5,
    )

    job = JobPosting(
        title="Machine Learning Engineering Intern",
        company="AI Labs",
        raw_description="Build RAG pipelines with LlamaIndex and vector databases.",
        technologies=["Python", "LlamaIndex", "ChromaDB", "FastAPI"],
        keywords=["RAG", "LLM", "Embeddings"],
    )

    results = retriever.retrieve_for_job(job=job, top_k=3)

    assert len(results) == 3
    context = format_retrieved_context(results)
    assert len(context) > 100
    assert "### [Guideline" in context
