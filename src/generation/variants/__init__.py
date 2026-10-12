"""Generation pipeline variants for research and evaluation (Phase P7).

Variants:
    B0: Deterministic fallback without LLM.
    B1: Current production pipeline (Hybrid RAG + Gemini LLM).
    B3: Full knowledge base in prompt (no retrieval + Gemini LLM).
"""

from __future__ import annotations

from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.b1_hybrid_rag import generate_b1
from src.generation.variants.b3_full_context import (
    generate_b3,
    generate_b3_verified,
)
from src.generation.variants.v1_verified import V1RoundTrace, V1Trace, generate_v1

__all__ = [
    "V1RoundTrace",
    "V1Trace",
    "generate_b0",
    "generate_b1",
    "generate_b3",
    "generate_b3_verified",
    "generate_v1",
]
