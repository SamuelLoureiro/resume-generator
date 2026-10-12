"""Unit tests for application configuration and model settings validation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.config import ALLOWED_GENERATION_MODELS, Settings


def test_default_settings() -> None:
    """Test default values for generation and judge models and temperatures."""
    settings = Settings(_env_file=None, google_api_key="test_key")
    assert settings.generation_model == "gemini-3.5-flash-lite"
    assert settings.judge_model == "gemini-3.1-flash-lite"
    assert settings.generation_temperature == 0.3
    assert settings.judge_temperature == 0.0
    assert settings.gemini_embedding_model == "models/gemini-embedding-001"


def test_backward_compatibility_properties() -> None:
    """Test that deprecated properties delegate correctly to generation settings."""
    settings = Settings(
        _env_file=None,
        google_api_key="test_key",
        generation_model="gemini-3.8-flash",
        generation_temperature=0.5,
    )
    assert settings.gemini_model == "gemini-3.8-flash"
    assert settings.gemini_temperature == 0.5


def test_allowed_generation_models_contains_expected() -> None:
    """Verify ALLOWED_GENERATION_MODELS constant contains pinned models."""
    assert "gemini-3.5-flash-lite" in ALLOWED_GENERATION_MODELS
    assert "gemini-3.8-flash" in ALLOWED_GENERATION_MODELS


def test_distinct_models_validation_success() -> None:
    """Settings instantiate successfully when generation and judge models differ."""
    settings = Settings(
        _env_file=None,
        google_api_key="test_key",
        generation_model="gemini-3.8-flash",
        judge_model="gemini-3.1-flash-lite",
    )
    assert settings.generation_model == "gemini-3.8-flash"
    assert settings.judge_model == "gemini-3.1-flash-lite"


def test_identical_models_validation_raises() -> None:
    """Settings must reject identical generation and judge models."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            google_api_key="test_key",
            generation_model="gemini-3.5-flash-lite",
            judge_model="gemini-3.5-flash-lite",
        )
    assert "must differ" in str(exc_info.value)
    assert "Generator and judge must be different models" in str(exc_info.value)


def test_identical_models_with_prefix_normalization_raises() -> None:
    """Validation must detect identical models even if one includes 'models/' prefix."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            google_api_key="test_key",
            generation_model="gemini-3.5-flash-lite",
            judge_model="models/gemini-3.5-flash-lite",
        )
    assert "must differ" in str(exc_info.value)


def test_identical_models_case_insensitive_raises() -> None:
    """Validation must detect identical models regardless of whitespace or casing."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            _env_file=None,
            google_api_key="test_key",
            generation_model="  GEMINI-3.5-FLASH-LITE  ",
            judge_model="gemini-3.5-flash-lite",
        )
    assert "must differ" in str(exc_info.value)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("generation_temperature", -0.1),
        ("generation_temperature", 2.1),
        ("judge_temperature", -0.5),
        ("judge_temperature", 3.0),
    ],
)
def test_temperature_range_validation(field: str, invalid_value: float) -> None:
    """Temperature settings must enforce 0.0 <= temp <= 2.0 range."""
    kwargs = {field: invalid_value, "google_api_key": "test_key", "_env_file": None}
    with pytest.raises(ValidationError):
        Settings(**kwargs)
