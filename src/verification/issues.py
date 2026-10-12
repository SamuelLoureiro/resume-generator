"""Normalize verifier and judge findings into actionable issues (phase P8, variant V1).

The V1 loop needs one flat, ordered list of problems for two consumers:

1. the error-guided regeneration prompt (``build_regeneration_feedback_prompt``), and
2. the deterministic repair step (:mod:`src.verification.repair`).

This module is pure and offline. It reads a :class:`VerificationReport` (M1a–c, M2, M4,
M5) and, optionally, a claim-judge payload (M1d). The judge payload is duck-typed (an
object with a ``claims`` list) so that this module does not import the LLM stack.
"""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from src.data.facts import SCOPE_LEVEL_NAMES, CandidateFacts
from src.data.resume import TailoredResume
from src.verification.report import VerificationReport

IssueKind = Literal[
    "unsupported_skill",
    "unsupported_number",
    "entity_mismatch",
    "inflated_verb",
    "fabricated_keyword",
    "judge_unsupported",
    "judge_inflated",
    "judge_unavailable",
    "format",
]
IssueSource = Literal["deterministic", "judge"]

TRUTH_KINDS: frozenset[str] = frozenset(
    {
        "unsupported_skill",
        "unsupported_number",
        "entity_mismatch",
        "inflated_verb",
        "fabricated_keyword",
        "judge_unsupported",
        "judge_inflated",
        "judge_unavailable",
    }
)
"""Issue kinds that concern truthfulness (fabrication / inflation / unverifiable).

``format`` issues are the only kind that is not about truthfulness.
"""

NON_FIXABLE_FORMAT_CHECKS: frozenset[str] = frozenset({"phone_format"})
"""M5 checks the generator cannot influence (the header is injected from the profile)."""

_BULLET_ID_RE = re.compile(
    r"^(?P<section>exp|experience|proj|project)s?_(?P<entry>\d+)_(?:bullet_?|b)?(?P<bullet>\d+)$",
    re.IGNORECASE,
)


class VerificationIssue(BaseModel):
    """One problem found in a generated resume.

    Attributes:
        kind: Issue category.
        source: ``deterministic`` (src/verification) or ``judge`` (claim-level judge).
        location: Where the problem is: a bullet id (``exp_0_bullet_1``,
            ``proj_2_bullet_0``), ``summary``, or a section path (``skills/...``).
        text: The offending text as written in the resume.
        detail: Why it is a problem (verifier or judge rationale).
        fact_id: Matched atomic fact, when known.
        scope_ceiling: Scope ceiling of that fact, when relevant.
        check: Name of the underlying check (e.g. M1c sub-kind or M5 check name).
        llm_fixable: Whether a regeneration can plausibly fix it.
    """

    model_config = ConfigDict(frozen=True)

    kind: IssueKind
    source: IssueSource
    location: str
    text: str
    detail: str
    fact_id: str | None = None
    scope_ceiling: int | None = None
    check: str | None = None
    llm_fixable: bool = True

    @property
    def is_truth_issue(self) -> bool:
        """True if the issue concerns truthfulness rather than format."""
        return self.kind in TRUTH_KINDS


def parse_bullet_id(bullet_id: str) -> tuple[str, int, int] | None:
    """Parse a bullet id into ``(section, entry_index, bullet_index)``.

    Tolerates the prefix variants seen in judge outputs (``exp_0_bullet_1``,
    ``experience_0_bullet_1``, ``proj_1_b0``).

    Args:
        bullet_id: Identifier as used by the claim judge.

    Returns:
        tuple[str, int, int] | None: ``("experience" | "project", i, j)``, or None if
        the id does not designate an experience/project bullet.
    """
    match = _BULLET_ID_RE.match((bullet_id or "").strip())
    if not match:
        return None
    section = "experience" if match.group("section").lower().startswith("exp") else "project"
    return section, int(match.group("entry")), int(match.group("bullet"))


def bullet_id_for(section: str, entry_index: int, bullet_index: int) -> str:
    """Build the canonical bullet id used by the claim judge."""
    prefix = "exp" if section == "experience" else "proj"
    return f"{prefix}_{entry_index}_bullet_{bullet_index}"


def locate_bullet(resume: TailoredResume, text: str) -> str | None:
    """Return the canonical id of the first bullet whose text equals ``text``."""
    target = (text or "").strip()
    for i, exp in enumerate(resume.experiences):
        for j, bullet in enumerate(exp.bullets):
            if bullet.strip() == target:
                return bullet_id_for("experience", i, j)
    for i, proj in enumerate(resume.projects):
        for j, bullet in enumerate(proj.bullets):
            if bullet.strip() == target:
                return bullet_id_for("project", i, j)
    return None


def _location_from_reason(reason: str) -> str:
    """Extract the ``(where)`` hint embedded in a fabrication reason, if any."""
    match = re.search(r"\(([^()]*/[^()]*)\)", reason)
    return match.group(1) if match else "resume"


_SUB_TO_KIND: dict[str, IssueKind] = {
    "a": "unsupported_skill",
    "b": "unsupported_number",
    "c": "entity_mismatch",
}


def _judge_claims(judge_payload: Any) -> list[Any]:
    claims = getattr(judge_payload, "claims", None)
    return list(claims) if claims else []


def collect_issues(
    resume: TailoredResume,
    report: VerificationReport,
    facts: CandidateFacts,
    judge_payload: Any | None = None,
    judge_error: str | None = None,
) -> list[VerificationIssue]:
    """Flatten a verification report and an optional judge payload into issues.

    Order: deterministic fabrication (M1a–c), inflation (M2), fabricated keywords (M4),
    judge verdicts (M1d), format (M5). Exact duplicates are dropped.

    Args:
        resume: The resume that was verified (used to locate bullets).
        report: Deterministic verification report.
        facts: Verified atomic facts (scope ceilings for judge-inflated claims).
        judge_payload: Claim-judge payload (object with ``claims``), or None.
        judge_error: Error message if the judge was required but failed. Produces a
            non-fixable ``judge_unavailable`` issue (fail-closed).

    Returns:
        list[VerificationIssue]: Ordered, de-duplicated issues.
    """
    issues: list[VerificationIssue] = []

    for claim in report.fabrication.unsupported:
        issues.append(
            VerificationIssue(
                kind=_SUB_TO_KIND[claim.sub],
                source="deterministic",
                location=_location_from_reason(claim.reason),
                text=claim.text,
                detail=claim.reason,
                check=claim.kind,
            )
        )

    for inflated in report.inflation.inflated:
        issues.append(
            VerificationIssue(
                kind="inflated_verb",
                source="deterministic",
                location=locate_bullet(resume, inflated.bullet) or "bullet",
                text=inflated.bullet,
                detail=inflated.reason,
                fact_id=inflated.fact_id,
                scope_ceiling=inflated.scope_ceiling,
                check="M2",
            )
        )

    if report.keywords is not None:
        for term in report.keywords.fabricated:
            issues.append(
                VerificationIssue(
                    kind="fabricated_keyword",
                    source="deterministic",
                    location="resume",
                    text=term,
                    detail=(
                        f"job keyword '{term}' appears in the resume but the candidate's "
                        "profile and facts do not support it"
                    ),
                    check="M4",
                )
            )

    if judge_error is not None:
        issues.append(
            VerificationIssue(
                kind="judge_unavailable",
                source="judge",
                location="resume",
                text="",
                detail=f"claim-level judge failed; free-text claims are unverified ({judge_error})",
                check="M1d",
                llm_fixable=False,
            )
        )

    for claim in _judge_claims(judge_payload):
        verdict = getattr(claim, "verdict", None)
        if verdict not in ("unsupported_claim", "inflated_scope"):
            continue
        fact_ids = list(getattr(claim, "matched_fact_ids", []) or [])
        ceiling: int | None = None
        for fid in fact_ids:
            fact = facts.get_by_id(fid)
            if fact is not None:
                ceiling = fact.scope_ceiling if ceiling is None else max(ceiling, fact.scope_ceiling)
        issues.append(
            VerificationIssue(
                kind="judge_unsupported" if verdict == "unsupported_claim" else "judge_inflated",
                source="judge",
                location=str(getattr(claim, "bullet_id", "") or "resume"),
                text=str(getattr(claim, "source_span", "") or ""),
                detail=str(getattr(claim, "rationale", "") or ""),
                fact_id=fact_ids[0] if fact_ids else None,
                scope_ceiling=ceiling,
                check=f"M1d/{getattr(claim, 'claim_type', 'other')}",
            )
        )

    for check in report.format.failed:
        issues.append(
            VerificationIssue(
                kind="format",
                source="deterministic",
                location="format",
                text=check.name,
                detail=check.detail or check.name,
                check=check.name,
                llm_fixable=check.name not in NON_FIXABLE_FORMAT_CHECKS,
            )
        )

    unique: list[VerificationIssue] = []
    seen: set[tuple[str, str, str, str]] = set()
    for issue in issues:
        key = (issue.kind, issue.location, issue.text, issue.detail)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return unique


def scope_hint(ceiling: int | None) -> str:
    """Human-readable scope ceiling, e.g. ``"level 2 (contributed)"``."""
    if ceiling is None:
        return "unknown level"
    return f"level {ceiling} ({SCOPE_LEVEL_NAMES.get(ceiling, '?')})"


def has_truth_issues(issues: list[VerificationIssue]) -> bool:
    """True if any issue concerns truthfulness."""
    return any(i.is_truth_issue for i in issues)


def has_fixable_issues(issues: list[VerificationIssue]) -> bool:
    """True if any issue can plausibly be fixed by regenerating."""
    return any(i.llm_fixable for i in issues)
