"""Data ingestion package for resume generator knowledge base."""

from src.ingestion.loader import KnowledgeBaseLoader, extract_title_from_markdown

__all__ = [
    "KnowledgeBaseLoader",
    "extract_title_from_markdown",
]
