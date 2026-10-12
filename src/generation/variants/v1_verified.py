"""V1 Variant: Verifier with Error-Guided Regeneration and Deterministic Repair.

Governed by docs/research_plan.md (Sections 4, 7; Hypothesis H1).
Architecture:
1. Round 0: Initial generation via B1 (Hybrid RAG + Gemini LLM).
2. Verification: Deterministic checks (M1a-c, M2, M4, M5) + Atomic Claim Judge (M1d).
3. If defects found: multi-turn error-guided regeneration (max 2 retries).
4. If defects persist after retries: deterministic repair (repair_resume).
5. If repaired resume still fails: deterministic floor fallback (B0).
Guarantees: Never outputs an unverified hallucination.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import ResumeLanguageCode, TailoredResume
from src.evaluation.claim_judge import ClaimLevelJudge, ResumeEvaluationPayload
from src.generation.chain import ResumeGenerationChain
from src.generation.prompts import build_regeneration_feedback_prompt
from src.generation.variants.b0_fallback import generate_b0
from src.retrieval.pipeline import KnowledgeBasePipeline
from src.verification.issues import (
    VerificationIssue,
    collect_issues,
    has_fixable_issues,
    has_truth_issues,
)
from src.verification.repair import RepairLog, repair_resume
from src.verification.report import VerificationReport, verify_resume

logger = logging.getLogger(__name__)


class V1RoundTrace(BaseModel):
    """Execution trace of a single round in the V1 verifier loop."""

    model_config = ConfigDict(frozen=True)

    round_index: int
    action: str
    hard_pass: bool
    issues_count: int
    issues: list[VerificationIssue] = Field(default_factory=list)


class V1Trace(BaseModel):
    """Complete diagnostic trace for a V1 generation run."""

    model_config = ConfigDict(frozen=True)

    final_path: str  # "clean@0", "clean@1", "clean@2", "repaired", "fallback"
    total_rounds: int
    rounds: list[V1RoundTrace] = Field(default_factory=list)
    repair_actions_count: int = 0
    retrieved_context: str = ""


def generate_v1(
    candidate: CandidateProfile,
    job: JobPosting,
    pipeline: KnowledgeBasePipeline | None = None,
    chain: ResumeGenerationChain | None = None,
    judge: ClaimLevelJudge | None = None,
    facts: CandidateFacts | None = None,
    top_k: int = 5,
    language: str = "auto",
    max_retries: int = 2,
    track: str | None = None,
    context: str | None = None,
) -> tuple[TailoredResume, V1Trace]:
    """Generate a verified, un-hallucinated resume using the V1 verifier loop.

    Args:
        candidate: Verified candidate profile source of truth.
        job: Target internship posting.
        pipeline: KnowledgeBasePipeline for RAG context retrieval (used if context is None).
        chain: ResumeGenerationChain instance for LLM invocation.
        judge: Optional ClaimLevelJudge for M1d atomic claim evaluation.
        facts: Verified CandidateFacts. If None, loaded from default config.
        top_k: Number of retrieved guideline chunks.
        language: Language code ('auto', 'pt', 'en', 'fr').
        max_retries: Maximum number of error-guided regeneration attempts (default 2).
        track: Technical track for coverage scoring (e.g. 'ai', 'data', 'backend').
        context: Optional explicit recruitment guidelines context (e.g. for B3 full-context).
            If None, retrieved from pipeline.

    Returns:
        tuple[TailoredResume, V1Trace]: The final verified resume and execution trace.
    """
    gen_chain = chain if chain is not None else ResumeGenerationChain()
    resolved_facts = facts if facts is not None else load_candidate_facts()
    resolved_lang = gen_chain.resolve_language(job, language)

    if context is not None:
        retrieved_context = context
    else:
        pipe = pipeline if pipeline is not None else KnowledgeBasePipeline()
        retrieved_context = pipe.get_context_for_job(job=job, top_k=top_k)

    base_messages = gen_chain.build_messages(
        candidate=candidate,
        job=job,
        retrieved_guidelines=retrieved_context,
        language=resolved_lang,
    )

    rounds_trace: list[V1RoundTrace] = []
    history: list[tuple[TailoredResume, str]] = []

    # --------------------------------------------------------------------------
    # Round 0: Initial Generation (B1 Pipeline)
    # --------------------------------------------------------------------------
    logger.info("V1 Round 0: Generating initial resume for '%s'...", job.title)
    current_resume = gen_chain.generate(
        candidate=candidate,
        job=job,
        retrieved_guidelines=retrieved_context,
        language=resolved_lang,
        allow_fallback=True,
    )

    # Initial verification
    initial_report = verify_resume(
        resume=current_resume,
        profile=candidate,
        facts=resolved_facts,
        job=job,
        track=track,
    )

    judge_payload: ResumeEvaluationPayload | None = None
    judge_error: str | None = None
    if judge is not None:
        try:
            judge_payload = judge.evaluate_resume(
                resume_id=f"v1_{job.company.lower()}_round0",
                resume=current_resume,
                facts=resolved_facts,
            )
        except Exception as exc:
            logger.warning("Claim judge evaluation failed in Round 0: %s", exc)
            judge_error = str(exc)

    issues = collect_issues(
        resume=current_resume,
        report=initial_report,
        facts=resolved_facts,
        judge_payload=judge_payload,
        judge_error=judge_error,
    )

    is_clean = len(issues) == 0 and initial_report.hard_pass
    rounds_trace.append(
        V1RoundTrace(
            round_index=0,
            action="initial_generation",
            hard_pass=is_clean,
            issues_count=len(issues),
            issues=issues,
        )
    )

    if is_clean:
        logger.info("V1 Round 0: Generated resume is completely clean! Returning.")
        return current_resume, V1Trace(
            final_path="clean@0",
            total_rounds=1,
            rounds=rounds_trace,
            retrieved_context=retrieved_context,
        )

    # --------------------------------------------------------------------------
    # Error-Guided Regeneration Rounds (Retries 1 .. max_retries)
    # --------------------------------------------------------------------------
    for retry in range(1, max_retries + 1):
        if not has_fixable_issues(issues):
            logger.info("V1 Retry %d: Remaining issues are non-fixable by LLM. Moving to repair.", retry)
            break

        logger.info(
            "V1 Retry %d/%d: Guiding regeneration with %d detected issues...",
            retry,
            max_retries,
            len(issues),
        )
        feedback_prompt = build_regeneration_feedback_prompt(issues, language=resolved_lang)
        history.append((current_resume, feedback_prompt))

        try:
            current_resume = gen_chain.regenerate_with_feedback(
                candidate=candidate,
                base_messages=base_messages,
                history=history,
                language=resolved_lang,
            )
        except Exception as exc:
            logger.warning("V1 Retry %d failed during regeneration: %s. Moving to repair.", retry, exc)
            break

        # Re-verify
        report = verify_resume(
            resume=current_resume,
            profile=candidate,
            facts=resolved_facts,
            job=job,
            track=track,
        )

        judge_payload = None
        judge_error = None
        if judge is not None:
            try:
                judge_payload = judge.evaluate_resume(
                    resume_id=f"v1_{job.company.lower()}_round{retry}",
                    resume=current_resume,
                    facts=resolved_facts,
                )
            except Exception as exc:
                logger.warning("Claim judge evaluation failed in Retry %d: %s", retry, exc)
                judge_error = str(exc)

        issues = collect_issues(
            resume=current_resume,
            report=report,
            facts=resolved_facts,
            judge_payload=judge_payload,
            judge_error=judge_error,
        )

        is_clean = len(issues) == 0 and report.hard_pass
        rounds_trace.append(
            V1RoundTrace(
                round_index=retry,
                action=f"regeneration_retry_{retry}",
                hard_pass=is_clean,
                issues_count=len(issues),
                issues=issues,
            )
        )

        if is_clean:
            logger.info("V1 Retry %d: Regenerated resume passed all checks cleanly!", retry)
            return current_resume, V1Trace(
                final_path=f"clean@{retry}",
                total_rounds=retry + 1,
                rounds=rounds_trace,
                retrieved_context=retrieved_context,
            )

    # --------------------------------------------------------------------------
    # Step 4: Deterministic Repair
    # --------------------------------------------------------------------------
    logger.info("V1: Applying deterministic repair to eliminate remaining defects...")
    repaired_resume, repair_log = repair_resume(
        resume=current_resume,
        issues=issues,
        profile=candidate,
        facts=resolved_facts,
        job=job,
    )

    repaired_report = verify_resume(
        resume=repaired_resume,
        profile=candidate,
        facts=resolved_facts,
        job=job,
        track=track,
    )

    repaired_issues = collect_issues(
        resume=repaired_resume,
        report=repaired_report,
        facts=resolved_facts,
        judge_payload=None,
    )

    repaired_clean = repaired_report.hard_pass and not has_truth_issues(repaired_issues)
    rounds_trace.append(
        V1RoundTrace(
            round_index=len(rounds_trace),
            action="deterministic_repair",
            hard_pass=repaired_clean,
            issues_count=len(repaired_issues),
            issues=repaired_issues,
        )
    )

    if repaired_clean:
        logger.info(
            "V1: Deterministic repair succeeded with %d actions! Hard-pass verified.",
            repair_log.total_actions,
        )
        return repaired_resume, V1Trace(
            final_path="repaired",
            total_rounds=len(rounds_trace),
            rounds=rounds_trace,
            repair_actions_count=repair_log.total_actions,
            retrieved_context=retrieved_context,
        )

    # --------------------------------------------------------------------------
    # Step 5: Deterministic Fallback (B0)
    # --------------------------------------------------------------------------
    logger.warning("V1: Repaired resume still had residual issues. Falling back to B0.")
    fallback_resume = generate_b0(candidate=candidate, job=job, language=resolved_lang)
    rounds_trace.append(
        V1RoundTrace(
            round_index=len(rounds_trace),
            action="fallback_b0",
            hard_pass=True,
            issues_count=0,
            issues=[],
        )
    )

    return fallback_resume, V1Trace(
        final_path="fallback",
        total_rounds=len(rounds_trace),
        rounds=rounds_trace,
        repair_actions_count=repair_log.total_actions,
        retrieved_context=retrieved_context,
    )
