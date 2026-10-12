"""Atomic claim-level evaluation judge powered by Gemini (gemini-3.1-flash-lite).

Governed by docs/research_plan.md (Section 6) and phase_p6_judge_validation_plan.md (v2).
Operates at atomic claim granularity with closed-world assumptions,
mandatory fact citations, relational binding checks, and fail-closed error handling.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Literal

from llama_index.core.llms import LLM, ChatMessage, MessageRole
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.config import get_settings
from src.data.facts import CandidateFacts
from src.data.resume import TailoredResume
from src.generation.chain import extract_json_payload, get_gemini_llm

logger = logging.getLogger(__name__)

CLAIM_JUDGE_PROMPT_VERSION = "claim_judge_v2.0"

ClaimType = Literal["action", "metric", "tool", "scope", "relational", "other"]
VerdictType = Literal["grounded", "partially_grounded", "unsupported_claim", "inflated_scope"]


class ClaimVerdict(BaseModel):
    """Evaluation verdict for an individual atomic claim within a resume bullet.

    Attributes:
        bullet_id: Identifier of the source resume bullet (e.g. 'exp_0_bullet_0').
        claim_id: Sub-claim index or identifier (e.g. 'claim_1').
        source_span: Verbatim substring from the resume bullet corresponding to this claim.
        claim_type: The nature of the claim (action, metric, tool, relational).
        rationale: Concise justification written BEFORE committing to the verdict (CoT).
        evidence_quote: Verbatim quote from the verified atomic fact supporting this claim.
        matched_fact_ids: List of atomic fact IDs providing evidence.
        extracted_scope_level: Extracted action verb scope level (1 to 4).
        verdict: Grounding verdict (grounded, partially_grounded, unsupported_claim, inflated_scope).
    """

    model_config = ConfigDict(frozen=True)

    bullet_id: str
    claim_id: str
    source_span: str
    claim_type: ClaimType = "other"
    rationale: str
    evidence_quote: str | None = None
    matched_fact_ids: list[str] = Field(default_factory=list)
    extracted_scope_level: int | None = None
    verdict: VerdictType

    @field_validator("claim_type", mode="before")
    @classmethod
    def normalize_claim_type(cls, v: Any) -> str:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ("action", "metric", "tool", "scope", "relational", "other"):
                return v_clean
        return "other"

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, v: Any) -> str:
        if isinstance(v, str):
            v_clean = v.strip().lower()
            if v_clean in ("grounded", "supported", "fully_grounded"):
                return "grounded"
            if v_clean in ("partially_grounded", "partial", "partially_supported"):
                return "partially_grounded"
            if v_clean in (
                "unsupported_claim",
                "unsupported",
                "hallucination",
                "relational",
                "conflation",
                "fabricated",
                "not_grounded",
            ):
                return "unsupported_claim"
            if v_clean in ("inflated_scope", "inflated", "scope_inflated"):
                return "inflated_scope"
        return v


class ResumeEvaluationPayload(BaseModel):
    """Container for all atomic claim verdicts of an evaluated resume.

    Attributes:
        resume_id: Identifier of the resume evaluated.
        prompt_version: Version of the judge prompt used.
        claims: List of individual atomic claim verdicts.
    """

    model_config = ConfigDict(frozen=True)

    resume_id: str
    prompt_version: str = CLAIM_JUDGE_PROMPT_VERSION
    claims: list[ClaimVerdict]

    @model_validator(mode="after")
    def validate_citations_and_coverage(self) -> "ResumeEvaluationPayload":
        """Enforce fail-closed rules on evaluator output."""
        if not self.claims:
            raise ValueError("Evaluator returned empty claims list (fail-closed)")
        for c in self.claims:
            if c.verdict == "grounded" and not c.matched_fact_ids:
                raise ValueError(f"Claim '{c.claim_id}' marked grounded without fact citation")
        return self

    @property
    def has_unsupported(self) -> bool:
        """True if any claim was judged unsupported or inflated."""
        return any(c.verdict in ("unsupported_claim", "inflated_scope") for c in self.claims)

    def claims_for_bullet(self, bullet_id: str) -> list[ClaimVerdict]:
        """Return all verdicts associated with a given bullet identifier."""
        return [c for c in self.claims if c.bullet_id == bullet_id]


def strip_latex_markup(text: str) -> str:
    """Clean LaTeX macros and comments to prevent context or label leaks.

    Args:
        text: Raw resume text.

    Returns:
        str: Plain text stripped of LaTeX formatting and comments.
    """
    if not text:
        return ""
    # 1. Strip LaTeX comments (% to end of line)
    text = re.sub(r"(?<!\\)%.*$", "", text, flags=re.MULTILINE)
    # 2. Unescape common symbols
    text = (
        text.replace(r"\%", "%")
        .replace(r"\&", "&")
        .replace(r"\_", "_")
        .replace(r"\#", "#")
        .replace(r"\$", "$")
    )
    # 3. Strip hyperref \href{url}{label} -> label
    text = re.sub(r"\\href\{[^}]*\}\{([^}]*)\}", r"\1", text)
    # 4. Strip command wrappers \textbf{foo} -> foo
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", text)
    # 5. Clean whitespace
    return re.sub(r"\s+", " ", text).strip()


JUDGE_SYSTEM_PROMPT = """You are a rigorous, adversarial verification judge evaluating whether claims in an internship resume are strictly supported by the candidate's verified atomic records.

CRITICAL MANDATES (CLOSED-WORLD ASSUMPTION):
1. The candidate is ONLY authorized to claim skills, metrics, and actions that are directly supported by the verified atomic facts provided.
2. DO NOT use world knowledge to assume unstated competencies. For example:
   - "Knowing Python" does NOT imply knowing Django or FastAPI.
   - "Doing ML research" does NOT imply training PyTorch models or writing CUDA kernels.
   - If a technology, metric, or task is absent from the verified facts, it is UNSUPPORTED.
3. RELATIONAL BINDING STRICTNESS:
   - A tool, metric, or responsibility used in Project A CANNOT be attributed to Project B.
   - If the candidate performed an action in a junior enterprise, claiming it for an academic project is UNSUPPORTED (the verdict MUST be "unsupported_claim").
4. SCOPE LADDER CEILING:
   - Level 1: participated in, assisted, supported
   - Level 2: contributed to, co-designed, helped build
   - Level 3: developed, built, implemented, integrated, trained, wrote
   - Level 4: led, managed, owned, founded, directed, coordinated, spearheaded
   - If the action verb level exceeds the fact's scope_ceiling (e.g. claiming "Architected" or "Spearheaded" when fact ceiling is 1 or 2), the verdict MUST be "inflated_scope".
5. REASONING FIRST (CHAIN-OF-THOUGHT):
   - You must write a concise `rationale` and provide an exact `evidence_quote` from the cited fact BEFORE committing to `verdict`.
   - If `verdict` is "grounded", `matched_fact_ids` must not be empty.
   - Allowed verdicts: "grounded", "partially_grounded", "unsupported_claim", "inflated_scope". NOTE: "relational" is a claim_type, NOT a verdict! The verdict for any relational error is "unsupported_claim".

Output format: pure JSON conforming to the schema:
{
  "resume_id": "<string>",
  "prompt_version": "claim_judge_v2.0",
  "claims": [
    {
      "bullet_id": "<string>",
      "claim_id": "<string>",
      "source_span": "<substring of bullet>",
      "claim_type": "action" | "metric" | "tool" | "scope" | "relational" | "other",
      "rationale": "<concise explanation>",
      "evidence_quote": "<verbatim quote from fact or null>",
      "matched_fact_ids": ["<fact_id>"],
      "extracted_scope_level": 1 | 2 | 3 | 4 | null,
      "verdict": "grounded" | "partially_grounded" | "unsupported_claim" | "inflated_scope"
    }
  ]
}
"""


def format_facts_for_judge(facts: CandidateFacts) -> str:
    """Format verified atomic facts into a structured prompt section."""
    lines = ["# VERIFIED ATOMIC CANDIDATE FACTS (GROUND TRUTH):"]
    for f in facts.facts:
        metrics_str = f", metrics={f.metrics}" if f.metrics else ""
        tags_str = f", tags={f.tags}" if f.tags else ""
        lines.append(
            f'- [FACT id="{f.id}", ceiling={f.scope_ceiling}{metrics_str}{tags_str}]\n  Text: "{f.text}"'
        )
    return "\n".join(lines)


def format_resume_bullets_for_judge(resume: TailoredResume) -> str:
    """Format resume entries and bullets with explicit IDs for the judge."""
    lines = ["# RESUME CONTENT TO VERIFY:"]

    if resume.objective_or_summary:
        clean_sum = strip_latex_markup(resume.objective_or_summary)
        lines.append(f'- [BULLET id="summary"] "{clean_sum}"')

    for e_idx, exp in enumerate(resume.experiences):
        org = strip_latex_markup(exp.organization)
        title = strip_latex_markup(exp.title)
        lines.append(f"\n## Experience: {title} at {org} ({exp.period})")
        for b_idx, b in enumerate(exp.bullets):
            clean_b = strip_latex_markup(b)
            lines.append(f'- [BULLET id="exp_{e_idx}_bullet_{b_idx}"] "{clean_b}"')

    for p_idx, proj in enumerate(resume.projects):
        p_name = strip_latex_markup(proj.name)
        lines.append(f"\n## Project: {p_name}")
        for b_idx, b in enumerate(proj.bullets):
            clean_b = strip_latex_markup(b)
            lines.append(f'- [BULLET id="proj_{p_idx}_bullet_{b_idx}"] "{clean_b}"')

    return "\n".join(lines)


class ClaimLevelJudge:
    """Atomic claim-level evaluator for grounded resume verification."""

    def __init__(self, llm: LLM | None = None, cache_dir: Path | None = None) -> None:
        """Initialize judge with optional dependency injection.

        Args:
            llm: LlamaIndex-compatible LLM. If None, initialized with settings.judge_model.
            cache_dir: Optional path to store and load evaluated payloads.
        """
        if llm is not None:
            self._llm = llm
        else:
            settings = get_settings()
            self._llm = get_gemini_llm(
                model_name=settings.judge_model,
                temperature=settings.judge_temperature,
            )
        self.cache_dir = cache_dir
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_key(self, resume_id: str, resume: TailoredResume, facts: CandidateFacts) -> str:
        """Compute deterministic hash key for caching."""
        facts_block = format_facts_for_judge(facts)
        resume_block = format_resume_bullets_for_judge(resume)
        model_name = getattr(self._llm, "model", "gemini")
        content = f"{resume_id}:{facts_block}:{resume_block}:{CLAIM_JUDGE_PROMPT_VERSION}:{model_name}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def is_cached(self, resume_id: str, resume: TailoredResume, facts: CandidateFacts) -> bool:
        """Check if an evaluation payload is already cached on disk."""
        if not self.cache_dir:
            return False
        key = self.get_cache_key(resume_id, resume, facts)
        return (self.cache_dir / f"{key}.json").exists()

    def evaluate_resume(
        self,
        resume_id: str,
        resume: TailoredResume,
        facts: CandidateFacts,
    ) -> ResumeEvaluationPayload:
        """Evaluate all bullets of a resume against atomic facts.

        Args:
            resume_id: Identifier for the resume.
            resume: TailoredResume instance.
            facts: Verified atomic facts ground truth.

        Returns:
            ResumeEvaluationPayload: Validated verdicts per claim.

        Raises:
            ValueError: If the judge produces malformed JSON or invalid output (fail-closed).
        """
        if self.cache_dir:
            key = self.get_cache_key(resume_id, resume, facts)
            cache_file = self.cache_dir / f"{key}.json"
            if cache_file.exists():
                logger.info("Loading cached evaluation for resume '%s'...", resume_id)
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return ResumeEvaluationPayload.model_validate(data)

        facts_block = format_facts_for_judge(facts)
        resume_block = format_resume_bullets_for_judge(resume)

        user_content = (
            f"Please evaluate the resume '{resume_id}' against the verified facts.\n\n"
            f"{facts_block}\n\n"
            f"{resume_block}\n\n"
            f"Decompose every bullet into atomic claims and output the evaluation JSON for resume_id='{resume_id}'."
        )

        messages = [
            ChatMessage(role=MessageRole.SYSTEM, content=JUDGE_SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=user_content),
        ]

        logger.info("Calling claim-level judge for resume '%s'...", resume_id)
        max_retries = 3
        backoff_seconds = 7.0
        response_text = ""

        for attempt in range(1, max_retries + 1):
            try:
                response = self._llm.chat(messages)
                response_text = response.message.content or ""
                break
            except Exception as exc:
                err_msg = str(exc).lower()
                if (
                    ("429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg)
                    and attempt < max_retries
                ):
                    logger.warning(
                        "Rate limit hit in claim judge (attempt %d/%d). Sleeping %.1fs...",
                        attempt,
                        max_retries,
                        backoff_seconds,
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 2.0
                else:
                    raise

        json_str = extract_json_payload(response_text)
        data = json.loads(json_str)

        if not isinstance(data, dict):
            raise ValueError(f"Judge output is not a JSON object for resume '{resume_id}'")

        data["resume_id"] = resume_id
        data["prompt_version"] = CLAIM_JUDGE_PROMPT_VERSION

        payload = ResumeEvaluationPayload.model_validate(data)

        # Mechanical scope check validation
        facts_by_id = {f.id: f for f in facts.facts}
        adjusted_claims: list[ClaimVerdict] = []
        for c in payload.claims:
            if c.extracted_scope_level and c.matched_fact_ids:
                # Check highest scope ceiling among cited facts
                max_ceiling = max(
                    facts_by_id[fid].scope_ceiling for fid in c.matched_fact_ids if fid in facts_by_id
                )
                if c.extracted_scope_level > max_ceiling and c.verdict == "grounded":
                    # Elevate to inflated_scope mechanically
                    c_dict = c.model_dump()
                    c_dict["verdict"] = "inflated_scope"
                    c_dict["rationale"] = (
                        f"{c.rationale} [Mechanical override: extracted scope level {c.extracted_scope_level} "
                        f"exceeds fact ceiling {max_ceiling}]"
                    )
                    adjusted_claims.append(ClaimVerdict.model_validate(c_dict))
                    continue
            adjusted_claims.append(c)

        result_payload = ResumeEvaluationPayload(
            resume_id=resume_id,
            prompt_version=CLAIM_JUDGE_PROMPT_VERSION,
            claims=adjusted_claims,
        )

        if self.cache_dir:
            key = self.get_cache_key(resume_id, resume, facts)
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(result_payload.model_dump_json(indent=2), encoding="utf-8")

        return result_payload
