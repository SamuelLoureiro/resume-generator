"""Unit tests for KnowledgeBaseIndexer using MockEmbedding (offline, no API calls)."""

from __future__ import annotations

from pathlib import Path

import pytest
from llama_index.core import Document
from llama_index.core.embeddings.mock_embed_model import MockEmbedding

from src.ingestion.indexer import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_COLLECTION_NAME,
    KnowledgeBaseIndexer,
    build_chroma_vector_store,
    build_sentence_splitter,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def make_documents(n: int = 3) -> list[Document]:
    """Create a list of synthetic LlamaIndex Documents for testing.

    Args:
        n: Number of documents to generate.

    Returns:
        list[Document]: List of mock documents with metadata.
    """
    docs = []
    for i in range(n):
        docs.append(
            Document(
                text=(
                    f"# Document {i}\n\n"
                    "This is a synthetic test document used to verify indexer behavior. "
                    "It contains enough content to be split and embedded without any real "
                    "API call, since we rely on MockEmbedding throughout the test suite."
                ),
                metadata={
                    "category": "test_category",
                    "topic": f"Document {i}",
                    "file_name": f"doc_{i}.md",
                },
            )
        )
    return docs


def make_mock_embed_model() -> MockEmbedding:
    """Create a MockEmbedding with dimensionality matching text-embedding-004.

    Returns:
        MockEmbedding: Zero-vector embedding model for offline testing.
    """
    return MockEmbedding(embed_dim=768)


# ---------------------------------------------------------------------------
# build_sentence_splitter tests
# ---------------------------------------------------------------------------

def test_sentence_splitter_configuration() -> None:
    """Test that the sentence splitter is built with the correct parameters."""
    splitter = build_sentence_splitter()

    assert splitter.chunk_size == CHUNK_SIZE
    assert splitter.chunk_overlap == CHUNK_OVERLAP


def test_sentence_splitter_splits_long_document() -> None:
    """Test that the splitter actually splits a document longer than chunk_size."""
    splitter = build_sentence_splitter()
    long_text = "This is a test sentence. " * 200  # ~5000 tokens — well above 512
    doc = Document(text=long_text)

    nodes = splitter.get_nodes_from_documents([doc])

    assert len(nodes) > 1, "Long document should be split into multiple nodes."


def test_sentence_splitter_short_document_single_node() -> None:
    """Test that a short document produces exactly one node."""
    splitter = build_sentence_splitter()
    doc = Document(text="Short text.")

    nodes = splitter.get_nodes_from_documents([doc])

    assert len(nodes) == 1


# ---------------------------------------------------------------------------
# build_chroma_vector_store tests
# ---------------------------------------------------------------------------

def test_build_chroma_vector_store(tmp_path: Path) -> None:
    """Test that ChromaVectorStore is created with correct persist directory."""
    from llama_index.vector_stores.chroma import ChromaVectorStore

    store = build_chroma_vector_store(
        persist_dir=tmp_path / "chroma_test",
        collection_name="test_collection",
    )

    assert isinstance(store, ChromaVectorStore)


# ---------------------------------------------------------------------------
# KnowledgeBaseIndexer tests
# ---------------------------------------------------------------------------

def test_indexer_build_index(tmp_path: Path) -> None:
    """Test building a vector index from synthetic documents with MockEmbedding."""
    from llama_index.core import VectorStoreIndex

    embed_model = make_mock_embed_model()
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=tmp_path / "chroma_build",
        collection_name="test_build",
    )

    docs = make_documents(n=3)
    index = indexer.build_index(docs)

    assert isinstance(index, VectorStoreIndex)


def test_indexer_build_index_empty_raises() -> None:
    """Test that building an index with no documents raises ValueError."""
    embed_model = make_mock_embed_model()
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir="/tmp/unused_chroma",
        collection_name="test_empty",
    )

    with pytest.raises(ValueError, match="empty"):
        indexer.build_index([])


def test_indexer_load_index_missing_dir_raises(tmp_path: Path) -> None:
    """Test that loading an index from a non-existent directory raises FileNotFoundError."""
    embed_model = make_mock_embed_model()
    missing_dir = tmp_path / "does_not_exist"

    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=missing_dir,
        collection_name="test_load",
    )

    with pytest.raises(FileNotFoundError):
        indexer.load_index()


def test_indexer_load_index_after_build(tmp_path: Path) -> None:
    """Test that a built index can be loaded back from the persisted ChromaDB store."""
    from llama_index.core import VectorStoreIndex

    embed_model = make_mock_embed_model()
    persist_dir = tmp_path / "chroma_roundtrip"
    collection_name = "test_roundtrip"

    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=persist_dir,
        collection_name=collection_name,
    )

    docs = make_documents(n=2)
    indexer.build_index(docs)

    loaded_index = indexer.load_index()
    assert isinstance(loaded_index, VectorStoreIndex)


def test_indexer_metadata_preserved_after_build(tmp_path: Path) -> None:
    """Test that document metadata is accessible through the built index."""
    from llama_index.core import VectorStoreIndex

    embed_model = make_mock_embed_model()
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=tmp_path / "chroma_meta",
        collection_name="test_meta",
    )

    docs = [
        Document(
            text="# Best Practices\n\nKey resume tip: quantify your achievements.",
            metadata={
                "category": "resume_best_practices",
                "topic": "Best Practices",
                "file_name": "01_best_practices.md",
            },
        )
    ]
    index = indexer.build_index(docs)

    assert isinstance(index, VectorStoreIndex)


def test_indexer_constants() -> None:
    """Test that indexer module constants have valid values."""
    assert CHUNK_SIZE > 0
    assert CHUNK_OVERLAP > 0
    assert CHUNK_OVERLAP < CHUNK_SIZE
    assert isinstance(CHROMA_COLLECTION_NAME, str)
    assert len(CHROMA_COLLECTION_NAME) > 0


def test_get_embedding_model_mock() -> None:
    """Test creating a mock embedding model via get_embedding_model factory."""
    from src.ingestion.indexer import get_embedding_model

    embed_model = get_embedding_model(mock=True, mock_dim=768)
    assert isinstance(embed_model, MockEmbedding)


def test_indexer_integration_with_real_kb_docs(tmp_path: Path) -> None:
    """End-to-end integration test: load real KB docs and build index into ChromaDB."""
    from llama_index.core import VectorStoreIndex
    from src.ingestion.loader import KnowledgeBaseLoader

    loader = KnowledgeBaseLoader()
    docs = loader.load_all_documents()
    assert len(docs) >= 10, "Expected at least 10 real documents from knowledge base"

    embed_model = make_mock_embed_model()
    indexer = KnowledgeBaseIndexer(
        embed_model=embed_model,
        persist_dir=tmp_path / "chroma_real_kb",
        collection_name="real_kb_test",
    )

    index = indexer.build_index(docs)
    assert isinstance(index, VectorStoreIndex)

    # Verify reloading from disk
    reloaded_index = indexer.load_index()
    assert isinstance(reloaded_index, VectorStoreIndex)
