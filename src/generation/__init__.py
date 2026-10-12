"""Generation package: prompts, LLM generation chain, and LaTeX PDF formatter."""

from src.generation.chain import (
    ResumeGenerationChain,
    build_fallback_tailored_resume,
    extract_json_payload,
    get_gemini_llm,
    parse_tailored_resume,
)
from src.generation.formatter import (
    ResumeFormatter,
    build_jinja_environment,
    sanitize_filename_part,
)
from src.generation.prompts import (
    SYSTEM_PROMPT,
    build_resume_generation_prompt,
    get_resume_schema_description,
)

__all__ = [
    "SYSTEM_PROMPT",
    "build_resume_generation_prompt",
    "get_resume_schema_description",
    "ResumeGenerationChain",
    "build_fallback_tailored_resume",
    "parse_tailored_resume",
    "extract_json_payload",
    "get_gemini_llm",
    "ResumeFormatter",
    "build_jinja_environment",
    "sanitize_filename_part",
]
