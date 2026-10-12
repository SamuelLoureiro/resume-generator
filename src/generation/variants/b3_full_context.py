"""B3 Variant: Full-context baseline without retrieval (Gemini LLM).

Tests hypothesis H4: Pasting the entire knowledge base (12 documents, ~5,400 words)
into the prompt without retrieval vs. RAG retrieval.
"""

from __future__ import annotations

import logging
from pathlib import Path

from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.generation.chain import ResumeGenerationChain
from src.ingestion.loader import KnowledgeBaseLoader

logger = logging.getLogger(__name__)


def load_full_knowledge_base_context(
    knowledge_base_dir: Path | str | None = None,
) -> str:
    """Load and concatenate all 12 knowledge base documents into a single prompt block.

    Args:
        knowledge_base_dir: Custom knowledge base directory path. If None, default from settings.

    Returns:
        str: Complete knowledge base text structured in Markdown.
    """
    loader = KnowledgeBaseLoader(knowledge_base_dir=knowledge_base_dir)
    docs = loader.load_all_documents()
    # Sort deterministically by category and filename
    docs = sorted(
        docs,
        key=lambda d: (
            d.metadata.get("category", ""),
            d.metadata.get("file_name", ""),
        ),
    )

    blocks: list[str] = [
        "# Complete Recruitment & Resume Best Practices Knowledge Base (12 Documents)"
    ]
    for doc in docs:
        title = doc.metadata.get("title", doc.metadata.get("file_name", "Guideline"))
        category = doc.metadata.get("category", "")
        content = doc.get_content().strip()
        blocks.append(f"## {title} [Categoria: {category}]\n\n{content}")

    return "\n\n---\n\n".join(blocks)


def generate_b3(
    candidate: CandidateProfile,
    job: JobPosting,
    chain: ResumeGenerationChain | None = None,
    full_kb_context: str | None = None,
    language: str = "auto",
    allow_fallback: bool = False,
) -> tuple[TailoredResume, str]:
    """Generate a resume using the B3 Full-Context baseline.

    Args:
        candidate: Verified candidate profile.
        job: Target internship posting.
        chain: ResumeGenerationChain instance. If None, instantiated.
        full_kb_context: Preloaded knowledge base string. If None, loaded from disk.
        language: Target language ('auto', 'pt', 'en', 'fr').
        allow_fallback: If True, falls back to deterministic resume on LLM error.

    Returns:
        tuple[TailoredResume, str]: Generated resume and the full KB context text.
    """
    gen_chain = chain if chain is not None else ResumeGenerationChain()
    context = full_kb_context if full_kb_context is not None else load_full_knowledge_base_context()

    resume = gen_chain.generate(
        candidate=candidate,
        job=job,
        retrieved_guidelines=context,
        allow_fallback=allow_fallback,
        language=language,
    )

    return resume, context


def generate_b3_verified(
    candidate: CandidateProfile,
    job: JobPosting,
    chain: ResumeGenerationChain | None = None,
    judge: Any | None = None,
    facts: Any | None = None,
    full_kb_context: str | None = None,
    language: str = "auto",
    max_retries: int = 2,
    track: str | None = None,
) -> tuple[TailoredResume, Any]:
    """Generate a verified resume using B3 Full-Context (no retrieval) + Verifier loop.

    Tests Hypothesis H4 (RAG Ablation): evaluates whether RAG retrieval outperforms
    pasting the complete knowledge base (12 docs) into the prompt when both pipelines
    are guarded by the same post-generation verifier.

    Args:
        candidate: Verified candidate profile source of truth.
        job: Target internship posting.
        chain: ResumeGenerationChain instance. If None, instantiated.
        judge: Optional ClaimLevelJudge for M1d atomic claim evaluation.
        facts: Verified atomic candidate facts. If None, loaded from default config.
        full_kb_context: Preloaded knowledge base string. If None, loaded from disk.
        language: Target language ('auto', 'pt', 'en', 'fr').
        max_retries: Maximum number of error-guided feedback retries.
        track: Job technical track for coverage scoring.

    Returns:
        tuple[TailoredResume, V1Trace]: Verified resume and diagnostic trace.
    """
    from src.generation.variants.v1_verified import generate_v1

    context = full_kb_context if full_kb_context is not None else load_full_knowledge_base_context()
    return generate_v1(
        candidate=candidate,
        job=job,
        chain=chain,
        judge=judge,
        facts=facts,
        language=language,
        max_retries=max_retries,
        track=track,
        context=context,
    )

