"""Resume generation chain powered by Google Gemini LLM via LlamaIndex."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from llama_index.core.llms import LLM, ChatMessage, MessageRole

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.generation.prompts import (
    SYSTEM_PROMPT,
    build_resume_generation_prompt,
)

logger = logging.getLogger(__name__)


def extract_json_payload(text: str) -> str:
    """Extract a clean JSON substring from an LLM response string.

    Handles raw JSON, markdown-wrapped JSON (```json ... ```), or text with
    leading/trailing commentary.

    Args:
        text: Raw response string from the language model.

    Returns:
        str: Isolated JSON string.

    Raises:
        ValueError: If no valid JSON object boundaries are found.
    """
    cleaned = text.strip()

    # Case 1: Markdown code block (```json ... ``` or ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Case 2: Direct JSON object (find outer braces)
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return cleaned[start_idx : end_idx + 1].strip()

    raise ValueError(f"Could not extract JSON payload from LLM response: {cleaned[:100]}...")


def parse_tailored_resume(raw_text: str) -> TailoredResume:
    """Parse and validate LLM output into a TailoredResume instance.

    Args:
        raw_text: Raw text string from the LLM.

    Returns:
        TailoredResume: Validated Pydantic resume model.

    Raises:
        ValueError: If JSON is invalid or fails Pydantic schema validation.
    """
    json_str = extract_json_payload(raw_text)
    try:
        data = json.loads(json_str)
        return TailoredResume.model_validate(data)
    except Exception as e:
        logger.error(
            "Failed to parse TailoredResume from JSON: %s\nPayload preview:\n%s",
            e,
            json_str[:300],
        )
        raise ValueError(f"Invalid TailoredResume structure: {e}") from e


def get_gemini_llm(
    model_name: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
) -> LLM:
    """Factory to create a configured Gemini LLM instance from LlamaIndex.

    Args:
        model_name: Identifier of the Gemini model. Defaults to settings.
        api_key: Gemini API key. Defaults to settings.
        temperature: Sampling temperature. Defaults to settings.

    Returns:
        LLM: Configured Gemini LLM adapter.
    """
    settings = get_settings()
    resolved_model = model_name or settings.gemini_model
    resolved_key = api_key or settings.google_api_key
    resolved_temp = temperature if temperature is not None else settings.gemini_temperature

    from llama_index.llms.gemini import Gemini

    return Gemini(
        model=resolved_model,
        api_key=resolved_key if resolved_key else None,
        temperature=resolved_temp,
    )


class ResumeGenerationChain:
    """Coordinates prompt construction, LLM invocation, and structured resume parsing.

    Attributes:
        llm: Language model adapter (Gemini in production, MockLLM in tests).
    """

    def __init__(self, llm: LLM | None = None) -> None:
        """Initialize the chain with an optional LLM instance.

        Args:
            llm: LLM instance. If None, initialized with get_gemini_llm().
        """
        self.llm = llm if llm is not None else get_gemini_llm()

    def generate(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        retrieved_guidelines: str = "",
    ) -> TailoredResume:
        """Generate a tailored resume customized for a specific internship role.

        Args:
            candidate: CandidateProfile holding factual background.
            job: Target JobPosting.
            retrieved_guidelines: Optional recruitment advice from RAG retrieval.

        Returns:
            TailoredResume: Structured, validated resume ready for LaTeX formatting.
        """
        user_prompt = build_resume_generation_prompt(
            candidate=candidate,
            job=job,
            retrieved_guidelines=retrieved_guidelines,
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]

        logger.info(
            "Invoking LLM for job '%s' at '%s'...",
            job.title,
            job.company,
        )

        response = self.llm.chat(messages)
        response_text = response.message.content or ""

        logger.info("LLM response received (%d chars). Parsing structure...", len(response_text))
        return parse_tailored_resume(response_text)
