"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Attributes:
        google_api_key: Google Gemini API key for LLM and embeddings.
        gemini_model: Gemini model identifier for text generation.
        gemini_temperature: Sampling temperature for the LLM.
        gemini_embedding_model: Gemini model identifier for text embeddings.
        chroma_persist_dir: Local directory for ChromaDB vector storage.
        output_dir: Directory for generated resumes (PDF/LaTeX).
        templates_dir: Directory containing LaTeX templates.
        knowledge_base_dir: Directory containing knowledge base Markdown documents.
        candidate_profile_path: File path to the candidate profile YAML.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini API Configuration
    google_api_key: str = Field(
        default="",
        description="Google Gemini API key for LLM and embeddings.",
    )

    # LLM Settings
    gemini_model: str = Field(
        default="gemini-2.5-flash",
        description="Gemini model identifier for text generation.",
    )
    gemini_temperature: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for the LLM.",
    )

    # Embedding Settings
    gemini_embedding_model: str = Field(
        default="models/text-embedding-004",
        description="Gemini model identifier for text embeddings.",
    )

    # Paths and Directories
    chroma_persist_dir: Path = Field(
        default=Path("./chroma_db"),
        description="Local directory for ChromaDB vector storage.",
    )
    output_dir: Path = Field(
        default=Path("./output"),
        description="Directory for generated resumes (PDF/LaTeX).",
    )
    templates_dir: Path = Field(
        default=Path("./templates"),
        description="Directory containing LaTeX templates.",
    )
    knowledge_base_dir: Path = Field(
        default=Path("./src/knowledge_base"),
        description="Directory containing knowledge base Markdown documents.",
    )
    candidate_profile_path: Path = Field(
        default=Path("./data/candidate_profile.yaml"),
        description="File path to the default candidate profile YAML.",
    )

    def ensure_directories(self) -> None:
        """Create necessary directories if they do not exist."""
        self.chroma_persist_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        self.knowledge_base_dir.mkdir(parents=True, exist_ok=True)
        self.candidate_profile_path.parent.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Retrieve cached application settings instance.

    Returns:
        Settings: The singleton application settings object.
    """
    settings = Settings()
    return settings
