"""RAG Core pipeline orchestrator: ties together loading, indexing, and hybrid retrieval."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from llama_index.core import VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import BaseNode, NodeWithScore

from src.config import get_settings
from src.data.job_posting import JobPosting
from src.ingestion.indexer import (
    CHROMA_COLLECTION_NAME,
    KnowledgeBaseIndexer,
    build_sentence_splitter,
    get_embedding_model,
)
from src.ingestion.loader import KnowledgeBaseLoader
from src.retrieval.retriever import (
    HybridResumeRetriever,
    format_retrieved_context,
)

logger = logging.getLogger(__name__)


def is_collection_populated(
    persist_dir: Path | str,
    collection_name: str = CHROMA_COLLECTION_NAME,
) -> bool:
    """Check whether a persistent ChromaDB collection exists and contains vectors.

    Args:
        persist_dir: Path to ChromaDB storage directory.
        collection_name: Name of the collection to check.

    Returns:
        bool: True if the collection exists and has at least one item.
    """
    path = Path(persist_dir)
    if not path.exists():
        return False

    try:
        client = chromadb.PersistentClient(path=str(path))
        collection = client.get_collection(name=collection_name)
        return collection.count() > 0
    except Exception:
        return False


class KnowledgeBasePipeline:
    """End-to-end RAG pipeline manager for knowledge base ingestion and retrieval.

    Orchestrates the complete lifecycle:
      1. Loading documents from knowledge base Markdown files.
      2. Chunking via SentenceSplitter (512 tokens / 50 overlap).
      3. Indexing into ChromaDB and building sparse BM25 nodes.
      4. Serving hybrid retrieval with Reciprocal Rank Fusion for job postings.

    Attributes:
        persist_dir: Local ChromaDB storage path.
        collection_name: Target ChromaDB collection name.
        embed_model: Embedding model adapter (Gemini in prod, Mock in tests).
        similarity_top_k: Top-K dense candidates retrieved from ChromaDB.
        bm25_top_k: Top-K sparse candidates retrieved from BM25.
    """

    def __init__(
        self,
        persist_dir: Path | str | None = None,
        collection_name: str = CHROMA_COLLECTION_NAME,
        embed_model: BaseEmbedding | None = None,
        similarity_top_k: int = 8,
        bm25_top_k: int = 8,
        knowledge_base_dir: Path | str | None = None,
    ) -> None:
        """Initialize KnowledgeBasePipeline with configurable settings.

        Args:
            persist_dir: ChromaDB persistence folder. If None, taken from settings.
            collection_name: ChromaDB collection name.
            embed_model: Embedding model instance. If None, built via get_embedding_model().
            similarity_top_k: Number of candidates from vector similarity search.
            bm25_top_k: Number of candidates from BM25 sparse keyword search.
            knowledge_base_dir: Custom knowledge base directory path.
        """
        settings = get_settings()
        self.persist_dir = Path(persist_dir) if persist_dir else Path(settings.chroma_persist_dir)
        self.collection_name = collection_name
        self.embed_model = embed_model if embed_model is not None else get_embedding_model()
        self.similarity_top_k = similarity_top_k
        self.bm25_top_k = bm25_top_k

        self.loader = KnowledgeBaseLoader(knowledge_base_dir=knowledge_base_dir)
        self.indexer = KnowledgeBaseIndexer(
            embed_model=self.embed_model,
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )

        self._index: VectorStoreIndex | None = None
        self._nodes: list[BaseNode] | None = None
        self._retriever: HybridResumeRetriever | None = None

    def is_indexed(self) -> bool:
        """Check if the knowledge base has already been indexed in ChromaDB.

        Returns:
            bool: True if ChromaDB contains stored vectors for the collection.
        """
        return is_collection_populated(self.persist_dir, self.collection_name)

    def setup(self, force_reindex: bool = False) -> None:
        """Set up the complete retrieval pipeline.

        Loads documents, splits into nodes for BM25, and builds or loads the
        ChromaDB vector index. Reuses existing vectors unless force_reindex is True.

        Args:
            force_reindex: If True, rebuilds the vector index from scratch even if
                the ChromaDB collection is already populated.
        """
        logger.info("Setting up KnowledgeBasePipeline (force_reindex=%s)...", force_reindex)

        # 1. Load source documents from disk
        docs = self.loader.load_all_documents()
        logger.info("Loaded %d source documents from knowledge base.", len(docs))

        # 2. Split into standardized chunks for BM25 sparse search
        splitter = build_sentence_splitter()
        self._nodes = splitter.get_nodes_from_documents(docs)
        logger.info("Generated %d chunk nodes via SentenceSplitter.", len(self._nodes))

        # 3. Build or load the ChromaDB vector index
        if not force_reindex and self.is_indexed():
            logger.info("Found existing ChromaDB index at %s. Loading...", self.persist_dir)
            self._index = self.indexer.load_index()
        else:
            logger.info("Building new ChromaDB index at %s (force_reindex=%s)...", self.persist_dir, force_reindex)
            self._index = self.indexer.build_index(docs, recreate=force_reindex)

        # 4. Initialize the Hybrid Retriever with Dense + Sparse components
        self._retriever = HybridResumeRetriever(
            index=self._index,
            nodes=self._nodes,
            similarity_top_k=self.similarity_top_k,
            bm25_top_k=self.bm25_top_k,
        )
        logger.info("KnowledgeBasePipeline setup complete and ready for retrieval.")

    def get_retriever(self) -> HybridResumeRetriever:
        """Get the initialized HybridResumeRetriever instance.

        Calls setup() automatically if the pipeline has not yet been initialized.

        Returns:
            HybridResumeRetriever: Active hybrid retriever.
        """
        if self._retriever is None:
            self.setup()
        assert self._retriever is not None
        return self._retriever

    def retrieve_for_job(
        self,
        job: JobPosting,
        top_k: int = 5,
        category: str | None = None,
    ) -> list[NodeWithScore]:
        """Execute hybrid retrieval for a job posting.

        Args:
            job: Target internship job posting.
            top_k: Number of advice and guideline chunks to retrieve.
            category: Optional category filter ('resume_best_practices', 'hr_recruitment').

        Returns:
            list[NodeWithScore]: Top ranked guidelines with RRF scores.
        """
        retriever = self.get_retriever()
        return retriever.retrieve_for_job(job=job, top_k=top_k, category=category)

    def get_context_for_job(
        self,
        job: JobPosting,
        top_k: int = 5,
        category: str | None = None,
    ) -> str:
        """Retrieve guidelines for a job and format directly as a clean prompt context block.

        Args:
            job: Target internship job posting.
            top_k: Number of advice chunks to retrieve.
            category: Optional category filter.

        Returns:
            str: Structured Markdown context ready for LLM prompt injection.
        """
        nodes = self.retrieve_for_job(job=job, top_k=top_k, category=category)
        return format_retrieved_context(nodes)
