"""B1 Variant: Current production pipeline (Hybrid RAG + Gemini LLM).

Ties together dense ChromaDB vector search + sparse BM25 keyword search with
Reciprocal Rank Fusion (RRF), passing top retrieved guideline chunks to
ResumeGenerationChain.
"""

from __future__ import annotations

from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.generation.chain import ResumeGenerationChain
from src.retrieval.pipeline import KnowledgeBasePipeline


def generate_b1(
    candidate: CandidateProfile,
    job: JobPosting,
    pipeline: KnowledgeBasePipeline | None = None,
    chain: ResumeGenerationChain | None = None,
    top_k: int = 5,
    language: str = "auto",
    allow_fallback: bool = False,
) -> tuple[TailoredResume, str]:
    """Generate a resume using the B1 Hybrid RAG pipeline.

    Args:
        candidate: Verified candidate profile.
        job: Target internship posting.
        pipeline: KnowledgeBasePipeline instance. If None, instantiated.
        chain: ResumeGenerationChain instance. If None, instantiated.
        top_k: Number of retrieved guideline chunks.
        language: Target language ('auto', 'pt', 'en', 'fr').
        allow_fallback: If True, falls back to deterministic resume on LLM error.

    Returns:
        tuple[TailoredResume, str]: Generated resume and retrieved context text.
    """
    pipe = pipeline if pipeline is not None else KnowledgeBasePipeline()
    gen_chain = chain if chain is not None else ResumeGenerationChain()

    retrieved_context = pipe.get_context_for_job(job=job, top_k=top_k)

    resume = gen_chain.generate(
        candidate=candidate,
        job=job,
        retrieved_guidelines=retrieved_context,
        allow_fallback=allow_fallback,
        language=language,
    )

    return resume, retrieved_context
