"""Document loader module for the resume generator knowledge base."""

from __future__ import annotations

import logging
from pathlib import Path
import re
from typing import Any

from llama_index.core import Document, SimpleDirectoryReader

from src.config import get_settings

logger = logging.getLogger(__name__)


def extract_title_from_markdown(content: str, default: str = "") -> str:
    """Extract the first H1 header title from markdown text.

    Args:
        content: Markdown content string.
        default: Fallback string if no header is found.

    Returns:
        str: Extracted title without leading '# ' or default.
    """
    for line in content.splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return default


class KnowledgeBaseLoader:
    """Loads and enriches documents from the knowledge base directory.

    Attributes:
        knowledge_base_dir: Root directory containing knowledge base categories.
    """

    def __init__(self, knowledge_base_dir: Path | str | None = None) -> None:
        """Initialize KnowledgeBaseLoader with the target directory.

        Args:
            knowledge_base_dir: Path to knowledge base root. If None, loaded from settings.
        """
        if knowledge_base_dir is not None:
            self.knowledge_base_dir = Path(knowledge_base_dir)
        else:
            self.knowledge_base_dir = Path(get_settings().knowledge_base_dir)

    def load_category(self, category_subdir: str) -> list[Document]:
        """Load all markdown documents from a specific subcategory directory.

        Args:
            category_subdir: Subdirectory name (e.g. 'resume_best_practices').

        Returns:
            list[Document]: Enriched LlamaIndex Document instances.

        Raises:
            FileNotFoundError: If the subcategory directory does not exist.
        """
        category_path = self.knowledge_base_dir / category_subdir
        if not category_path.exists() or not category_path.is_dir():
            raise FileNotFoundError(
                f"Knowledge base category directory not found: {category_path}"
            )

        md_files = list(category_path.rglob("*.md")) + list(category_path.rglob("*.markdown"))
        if not md_files:
            logger.warning(
                "Category directory '%s' contains no markdown files. Skipping.",
                category_subdir,
            )
            return []

        reader = SimpleDirectoryReader(
            input_dir=str(category_path),
            required_exts=[".md", ".markdown"],
            recursive=True,
        )

        documents = reader.load_data()
        enriched_documents: list[Document] = []

        for doc in documents:
            file_name = doc.metadata.get("file_name", "")
            raw_text = doc.text or ""
            topic = extract_title_from_markdown(raw_text, default=file_name)

            doc.metadata["category"] = category_subdir
            doc.metadata["topic"] = topic
            doc.metadata["file_name"] = file_name
            enriched_documents.append(doc)

        logger.info(
            "Loaded %d documents from category '%s'",
            len(enriched_documents),
            category_subdir,
        )
        return enriched_documents

    def load_all_documents(self) -> list[Document]:
        """Load and aggregate documents across all knowledge base categories.

        Scans known categories ('resume_best_practices', 'hr_recruitment', 'resume_examples')
        and any other subdirectories present in knowledge_base_dir.

        Returns:
            list[Document]: Aggregated list of all enriched Document instances.

        Raises:
            FileNotFoundError: If the root knowledge_base_dir does not exist.
        """
        if not self.knowledge_base_dir.exists():
            raise FileNotFoundError(
                f"Knowledge base root directory not found: {self.knowledge_base_dir}"
            )

        all_docs: list[Document] = []
        subdirs = [p for p in self.knowledge_base_dir.iterdir() if p.is_dir()]

        if not subdirs:
            logger.warning("No category subdirectories found in: %s", self.knowledge_base_dir)
            return []

        for subdir in sorted(subdirs):
            category_name = subdir.name
            try:
                category_docs = self.load_category(category_name)
                all_docs.extend(category_docs)
            except Exception as e:
                logger.error("Error loading category '%s': %s", category_name, e)

        logger.info(
            "Successfully loaded a total of %d documents from %s",
            len(all_docs),
            self.knowledge_base_dir,
        )
        return all_docs
