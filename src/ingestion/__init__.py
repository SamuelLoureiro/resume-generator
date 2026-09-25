"""Data ingestion package: document loading and vector index building."""

from src.ingestion.indexer import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    CHROMA_COLLECTION_NAME,
    KnowledgeBaseIndexer,
    build_chroma_vector_store,
    build_sentence_splitter,
)
from src.ingestion.loader import KnowledgeBaseLoader, extract_title_from_markdown

__all__ = [
    "KnowledgeBaseLoader",
    "extract_title_from_markdown",
    "KnowledgeBaseIndexer",
    "build_sentence_splitter",
    "build_chroma_vector_store",
    "CHUNK_SIZE",
    "CHUNK_OVERLAP",
    "CHROMA_COLLECTION_NAME",
]
