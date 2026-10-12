"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Pinned models configuration
ALLOWED_GENERATION_MODELS: list[str] = [
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file.

    Attributes:
        google_api_key: Google Gemini API key for LLM and embeddings.
        generation_model: Gemini model identifier for text generation (resume generator).
        judge_model: Gemini model identifier for evaluation judge.
        generation_temperature: Sampling temperature for text generation.
        judge_temperature: Sampling temperature for evaluation judge.
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
    generation_model: str = Field(
        default="gemini-3.5-flash-lite",
        description="Gemini model identifier for text generation (resume generator).",
    )
    judge_model: str = Field(
        default="gemini-3.1-flash-lite",
        description="Gemini model identifier for evaluation judge.",
    )
    generation_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for text generation.",
    )
    judge_temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=2.0,
        description="Sampling temperature for evaluation judge.",
    )

    # Embedding Settings
    gemini_embedding_model: str = Field(
        default="models/gemini-embedding-001",
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
    candidate_facts_path: Path = Field(
        default=Path("./data/candidate_facts.yaml"),
        description="File path to the verified candidate atomic facts YAML.",
    )

    @property
    def gemini_model(self) -> str:
        """Deprecated alias for generation_model for backward compatibility."""
        return self.generation_model

    @property
    def gemini_temperature(self) -> float:
        """Deprecated alias for generation_temperature for backward compatibility."""
        return self.generation_temperature

    @staticmethod
    def _normalize_model(model_name: str) -> str:
        cleaned = model_name.strip()
        if cleaned.startswith("models/"):
            cleaned = cleaned[len("models/") :]
        return cleaned.lower()

    @model_validator(mode="after")
    def validate_generator_and_judge_differ(self) -> "Settings":
        """Ensure generator and judge models are distinct to avoid self-evaluation bias."""
        gen_norm = self._normalize_model(self.generation_model)
        judge_norm = self._normalize_model(self.judge_model)
        if gen_norm == judge_norm:
            raise ValueError(
                f"GENERATION_MODEL ('{self.generation_model}') and JUDGE_MODEL ('{self.judge_model}') "
                "must differ. Generator and judge must be different models to prevent self-evaluation bias."
            )
        return self

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
