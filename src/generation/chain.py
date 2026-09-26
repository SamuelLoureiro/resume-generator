"""Resume generation chain powered by Google Gemini LLM via LlamaIndex."""

from __future__ import annotations

import json
import logging
import re
import time
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
        if isinstance(data, dict):
            # 1. Normalize header
            if "header" not in data and "contact" in data:
                data["header"] = data.pop("contact")

            # 2. Normalize objective
            if "objective_or_summary" not in data:
                for k in ["professional_objective", "objective", "summary"]:
                    if k in data:
                        data["objective_or_summary"] = data.pop(k)
                        break

            # 3. Normalize education period
            if "education" in data and isinstance(data["education"], list):
                for edu in data["education"]:
                    if isinstance(edu, dict) and "period" not in edu:
                        start = edu.get("start_date", "")
                        end = edu.get("end_date", "")
                        edu["period"] = f"{start} - {end}".strip(" -") or "Present"

            # 4. Normalize experience period
            if "experiences" in data and isinstance(data["experiences"], list):
                for exp in data["experiences"]:
                    if isinstance(exp, dict) and "period" not in exp:
                        start = exp.get("start_date", "")
                        end = exp.get("end_date", "")
                        exp["period"] = f"{start} - {end}".strip(" -") or "Present"

            # 5. Normalize skills
            if "skills" in data and isinstance(data["skills"], dict):
                skills_list = []
                for cat_key, skill_items in data["skills"].items():
                    cat_name = cat_key.replace("_", " ").title()
                    if isinstance(skill_items, list):
                        skills_list.append({"category_name": cat_name, "skills": [str(s) for s in skill_items]})
                data["skills"] = skills_list
            elif "skills_categories" in data and "skills" not in data:
                data["skills"] = data.pop("skills_categories")

            # 6. Normalize certifications
            if "certifications" in data and isinstance(data["certifications"], list):
                cert_strings = []
                for cert in data["certifications"]:
                    if isinstance(cert, dict):
                        name = cert.get("name", "")
                        issuer = cert.get("issuer", "")
                        date = cert.get("issue_date", "")
                        detail = f"{name} ({issuer}, {date})" if issuer and date else (f"{name} ({issuer})" if issuer else name)
                        cert_strings.append(detail)
                    elif isinstance(cert, str):
                        cert_strings.append(cert)
                data["certifications"] = cert_strings

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
    if any(m in resolved_model for m in ["gemini-2.5-flash", "gemini-3.8-flash"]):
        resolved_model = "models/gemini-flash-lite-latest"
    elif not resolved_model.startswith("models/"):
        resolved_model = f"models/{resolved_model}"
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

        max_retries = 3
        backoff_seconds = 7.0
        response_text = ""

        for attempt in range(1, max_retries + 1):
            try:
                response = self.llm.chat(messages)
                response_text = response.message.content or ""
                break
            except Exception as exc:
                err_msg = str(exc).lower()
                if ("429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg) and attempt < max_retries:
                    logger.warning(
                        "Rate limit exceeded (attempt %d/%d). Sleeping %.1fs before retrying...",
                        attempt,
                        max_retries,
                        backoff_seconds,
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 1.5
                else:
                    raise

        logger.info("LLM response received (%d chars). Parsing structure...", len(response_text))
        return parse_tailored_resume(response_text)
