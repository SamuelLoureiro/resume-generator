"""Document indexing module: chunking, embedding, and vector store persistence."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import chromadb
from llama_index.core import Document, StorageContext, VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore

from src.config import get_settings

logger = logging.getLogger(__name__)

# Chunking constants
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
CHROMA_COLLECTION_NAME = "resume_knowledge_base"


def build_sentence_splitter() -> SentenceSplitter:
    """Create a SentenceSplitter with project-standard chunking parameters.

    Returns:
        SentenceSplitter: Configured splitter with 512-token chunks and 50-token overlap.
    """
    return SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def get_embedding_model(
    model_name: str | None = None,
    api_key: str | None = None,
    mock: bool = False,
    mock_dim: int = 768,
) -> BaseEmbedding:
    """Create an embedding model instance for indexing and retrieval.

    Args:
        model_name: Gemini embedding model identifier. Defaults to settings.
        api_key: Optional Gemini API key. Defaults to settings.
        mock: If True, returns MockEmbedding (offline, zero API calls).
        mock_dim: Vector dimension for MockEmbedding (768 for text-embedding-004).

    Returns:
        BaseEmbedding: Configured embedding model adapter.
    """
    if mock:
        from llama_index.core.embeddings.mock_embed_model import MockEmbedding
        return MockEmbedding(embed_dim=mock_dim)

    from llama_index.embeddings.gemini import GeminiEmbedding

    settings = get_settings()
    resolved_model = model_name or settings.gemini_embedding_model
    if "text-embedding-004" in resolved_model:
        resolved_model = settings.gemini_embedding_model
    resolved_key = api_key or settings.google_api_key

    return GeminiEmbedding(
        model_name=resolved_model,
        api_key=resolved_key if resolved_key else None,
    )


def build_chroma_vector_store(
    persist_dir: Path | str | None = None,
    collection_name: str = CHROMA_COLLECTION_NAME,
    recreate: bool = False,
) -> ChromaVectorStore:
    """Create and configure a ChromaDB-backed vector store.

    Args:
        persist_dir: Directory for ChromaDB persistence. If None, loaded from settings.
        collection_name: Name of the ChromaDB collection to use.
        recreate: If True, deletes any existing collection with this name first.

    Returns:
        ChromaVectorStore: Configured LlamaIndex ChromaDB vector store adapter.
    """
    if persist_dir is None:
        persist_dir = get_settings().chroma_persist_dir

    persist_path = Path(persist_dir)
    persist_path.mkdir(parents=True, exist_ok=True)

    chroma_client = chromadb.PersistentClient(path=str(persist_path))
    if recreate:
        try:
            chroma_client.delete_collection(name=collection_name)
            logger.info("Deleted existing ChromaDB collection '%s' for recreation.", collection_name)
        except Exception:
            pass
    collection = chroma_client.get_or_create_collection(name=collection_name)

    logger.info(
        "ChromaDB collection '%s' ready at: %s",
        collection_name,
        persist_path,
    )

    return ChromaVectorStore(chroma_collection=collection)


class KnowledgeBaseIndexer:
    """Indexes knowledge base documents into a ChromaDB vector store.

    Handles document chunking via SentenceSplitter and embedding generation
    via a configurable embedding model (GeminiEmbedding in production,
    MockEmbedding for offline testing).

    Attributes:
        embed_model: Embedding model used to generate document vectors.
        persist_dir: Directory used for ChromaDB persistence.
        collection_name: ChromaDB collection name for the knowledge base.
    """

    def __init__(
        self,
        embed_model: BaseEmbedding | None = None,
        persist_dir: Path | str | None = None,
        collection_name: str = CHROMA_COLLECTION_NAME,
    ) -> None:
        """Initialize KnowledgeBaseIndexer.

        Args:
            embed_model: Embedding model instance. If None, built via get_embedding_model().
            persist_dir: Directory for ChromaDB persistence. Defaults to settings value.
            collection_name: Name of the ChromaDB collection.
        """
        self.embed_model = embed_model if embed_model is not None else get_embedding_model()
        self.persist_dir = Path(persist_dir) if persist_dir else Path(get_settings().chroma_persist_dir)
        self.collection_name = collection_name

    def build_index(
        self,
        documents: list[Document],
        recreate: bool = False,
    ) -> VectorStoreIndex:
        """Chunk, embed, and persist documents into ChromaDB.

        Applies SentenceSplitter to all documents, generates embeddings for
        each chunk, and stores the result in a persistent ChromaDB collection.

        Args:
            documents: List of LlamaIndex Document instances to index.
            recreate: If True, resets/recreates the vector store collection first.

        Returns:
            VectorStoreIndex: Populated index backed by the ChromaDB vector store.

        Raises:
            ValueError: If the documents list is empty.
        """
        if not documents:
            raise ValueError("Cannot build index from an empty document list.")

        logger.info(
            "Starting indexing: %d documents into collection '%s' (recreate=%s)",
            len(documents),
            self.collection_name,
            recreate,
        )

        vector_store = build_chroma_vector_store(
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
            recreate=recreate,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        splitter = build_sentence_splitter()

        index = VectorStoreIndex.from_documents(
            documents=documents,
            storage_context=storage_context,
            embed_model=self.embed_model,
            transformations=[splitter],
            show_progress=False,
        )

        logger.info(
            "Indexing complete. %d source documents stored in collection '%s'.",
            len(documents),
            self.collection_name,
        )

        return index

    def load_index(self) -> VectorStoreIndex:
        """Load an existing index from the persisted ChromaDB collection.

        Returns:
            VectorStoreIndex: Index loaded from the existing ChromaDB collection.

        Raises:
            FileNotFoundError: If the ChromaDB persist directory does not exist.
        """
        if not self.persist_dir.exists():
            raise FileNotFoundError(
                f"ChromaDB persist directory not found: {self.persist_dir}"
            )

        vector_store = build_chroma_vector_store(
            persist_dir=self.persist_dir,
            collection_name=self.collection_name,
        )
        storage_context = StorageContext.from_defaults(vector_store=vector_store)

        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=self.embed_model,
            storage_context=storage_context,
        )

        logger.info(
            "Loaded existing index from collection '%s' at: %s",
            self.collection_name,
            self.persist_dir,
        )

        return index
