"""Seeded synthetic lie injection harness for evaluation benchmarking.

Governed by docs/research_plan.md (Section 6) and phase_p6_judge_validation_plan.md (v2).
Provides deterministic, reproducible defect injection across 6 classes:
- L1 (fake_skill): Injects unverified technologies (detected by M1a).
- L2 (fake_number): Mutates numerical metrics (detected by M1b).
- L3 (inflated_verb): Escalates lead verbs above fact scope ceilings (detected by M2).
- L4 (fake_entity_date): Alters institutions, companies, or dates (detected by M1c).
- L5 (fabricated_responsibility): Naturalistic evidence ablation or ungrounded prose (detected by claim_judge_llm).
- L6 (cross_project_conflation): Splices facts/tools between different projects (detected by claim_judge_llm).
"""

from __future__ import annotations

import copy
import hashlib
import random
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from src.data.candidate import CandidateProfile
from src.data.facts import AtomicFact, CandidateFacts
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.verification.ground_truth import GroundTruth, extract_numbers
from src.verification.matching import match_resume_bullets
from src.verification.verb_ladder import extract_lead_verb

DefectClass = Literal[
    "fake_skill",
    "fake_number",
    "inflated_verb",
    "fake_entity_date",
    "fabricated_responsibility",
    "cross_project_conflation",
    "meta_word",
    "job_phrase_echo",
    "fused_facts",
]


class GroundTruthInjection(BaseModel):
    """Audit record of a synthetic defect injected into a resume.

    Attributes:
        mutation_id: Unique identifier for this mutation.
        resume_id: Identifier of the target resume.
        defect_class: The defect class (L1 to L6).
        target_section: Section path where injection occurred.
        bullet_id: Identifier or index of the altered bullet/field.
        original_text: Clean original text prior to mutation.
        injected_text: Mutated text containing the lie.
        injected_span: Precise substring/token representing the defect.
        expected_verdict: Expected judge classification.
        expected_detector: Which system is expected to detect it.
        ablated_fact_id: If defect is evidence ablation (L5), the removed fact ID.
    """

    model_config = ConfigDict(frozen=True)

    mutation_id: str
    resume_id: str
    defect_class: DefectClass
    target_section: str
    bullet_id: str
    original_text: str
    injected_text: str
    injected_span: str
    expected_verdict: Literal["unsupported_claim", "inflated_scope"]
    expected_detector: Literal["deterministic_p5", "claim_judge_llm"]
    ablated_fact_id: str | None = None


class CorruptedResume(BaseModel):
    """A mutated resume bundled with its ground-truth injection audit ledger.

    Attributes:
        resume_id: Identifier for the corrupted resume.
        resume: The mutated TailoredResume.
        injections: List of injected defects.
        active_facts: Ground-truth facts view (with ablated facts removed if L5).
    """

    model_config = ConfigDict(frozen=True)

    resume_id: str
    resume: TailoredResume
    injections: list[GroundTruthInjection]
    active_facts: CandidateFacts


def _stable_rng(seed: int, *keys: str) -> random.Random:
    """Derive a reproducible Random instance from seed and string keys using SHA-256."""
    token = f"{seed}:" + ":".join(keys)
    h = hashlib.sha256(token.encode("utf-8")).hexdigest()
    int_seed = int(h[:16], 16)
    return random.Random(int_seed)


# ---------------------------------------------------------------------------
# Individual Injections (by replacement)
# ---------------------------------------------------------------------------

CANDIDATE_FAKE_SKILLS = [
    "Kubernetes",
    "Rust",
    "Apache Spark",
    "GraphQL",
    "Solidity",
    "Terraform",
    "Elixir",
    "Apache Kafka",
    "Haskell",
    "Snowflake",
]

INFLATION_VERBS = ["Architected", "Spearheaded", "Directed", "Engineered", "Pioneered"]


def inject_fake_skill(
    resume: TailoredResume,
    truth: GroundTruth,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject an unverified technical skill (L1) by replacement."""
    rng = _stable_rng(seed, resume_id, "fake_skill")
    mut_resume = copy.deepcopy(resume)

    # Pick a fake skill that is definitely NOT in candidate allowlist
    fake_skill = next(s for s in CANDIDATE_FAKE_SKILLS if not truth.is_allowed_skill(s))

    # Priority 1: Replace a skill in resume.skills
    if mut_resume.skills and mut_resume.skills[0].skills:
        cat_idx = rng.randrange(len(mut_resume.skills))
        cat = mut_resume.skills[cat_idx]
        skill_idx = rng.randrange(len(cat.skills))
        orig_skill = cat.skills[skill_idx]

        cat.skills[skill_idx] = fake_skill
        injection = GroundTruthInjection(
            mutation_id=f"mut_{resume_id}_L1_{seed}",
            resume_id=resume_id,
            defect_class="fake_skill",
            target_section=f"skills[{cat_idx}]",
            bullet_id=f"skill_{cat_idx}_{skill_idx}",
            original_text=orig_skill,
            injected_text=fake_skill,
            injected_span=fake_skill,
            expected_verdict="unsupported_claim",
            expected_detector="deterministic_p5",
        )
        return mut_resume, injection

    # Priority 2: Replace in project technologies
    for proj_idx, proj in enumerate(mut_resume.projects):
        if proj.technologies:
            tech_idx = rng.randrange(len(proj.technologies))
            orig_skill = proj.technologies[tech_idx]
            proj.technologies[tech_idx] = fake_skill
            injection = GroundTruthInjection(
                mutation_id=f"mut_{resume_id}_L1_{seed}",
                resume_id=resume_id,
                defect_class="fake_skill",
                target_section=f"projects[{proj_idx}].technologies",
                bullet_id=f"proj_{proj_idx}_tech_{tech_idx}",
                original_text=orig_skill,
                injected_text=fake_skill,
                injected_span=fake_skill,
                expected_verdict="unsupported_claim",
                expected_detector="deterministic_p5",
            )
            return mut_resume, injection

    raise ValueError(f"Resume {resume_id} has no skills or project technologies to mutate.")


def inject_fake_number(
    resume: TailoredResume,
    truth: GroundTruth,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject an unverified numerical metric (L2) by mutating an existing number in a bullet."""
    rng = _stable_rng(seed, resume_id, "fake_number")
    mut_resume = copy.deepcopy(resume)

    # Search for bullets containing extractable numbers
    candidates: list[tuple[str, int, int, str]] = []  # (section, entry_idx, bullet_idx, bullet_text)
    for exp_idx, exp in enumerate(mut_resume.experiences):
        for b_idx, b in enumerate(exp.bullets):
            if extract_numbers(b):
                candidates.append(("experiences", exp_idx, b_idx, b))
    for proj_idx, proj in enumerate(mut_resume.projects):
        for b_idx, b in enumerate(proj.bullets):
            if extract_numbers(b):
                candidates.append(("projects", proj_idx, b_idx, b))

    if not candidates:
        # If no bullet has a number, pick a bullet and insert an invented metric
        if mut_resume.experiences and mut_resume.experiences[0].bullets:
            b_orig = mut_resume.experiences[0].bullets[0]
            fake_metric = "73% latency reduction"
            b_injected = f"{b_orig.rstrip('.')} achieving {fake_metric}."
            mut_resume.experiences[0].bullets[0] = b_injected
            return mut_resume, GroundTruthInjection(
                mutation_id=f"mut_{resume_id}_L2_{seed}",
                resume_id=resume_id,
                defect_class="fake_number",
                target_section="experiences[0].bullets[0]",
                bullet_id="exp_0_bullet_0",
                original_text=b_orig,
                injected_text=b_injected,
                injected_span=fake_metric,
                expected_verdict="unsupported_claim",
                expected_detector="deterministic_p5",
            )
        raise ValueError(f"Resume {resume_id} has no bullets to inject a number into.")

    chosen = candidates[rng.randrange(len(candidates))]
    section, entry_idx, b_idx, orig_text = chosen
    numbers = extract_numbers(orig_text)
    orig_num = numbers[0]

    # Create mutated number guaranteed not supported
    suffix = "%" if "%" in orig_num else ("+" if "+" in orig_num else "")
    digits = re.sub(r"[^\d]", "", orig_num)
    val = int(digits) if digits else 15
    new_val = val * 3 + 17  # prime offset
    fake_num = f"{new_val}{suffix}"
    while truth.is_supported_number(fake_num):
        new_val += 7
        fake_num = f"{new_val}{suffix}"

    injected_text = orig_text.replace(orig_num, fake_num, 1)
    if section == "experiences":
        mut_resume.experiences[entry_idx].bullets[b_idx] = injected_text
    else:
        mut_resume.projects[entry_idx].bullets[b_idx] = injected_text

    b_prefix = "exp" if section == "experiences" else "proj"
    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_L2_{seed}",
        resume_id=resume_id,
        defect_class="fake_number",
        target_section=f"{section}[{entry_idx}].bullets[{b_idx}]",
        bullet_id=f"{b_prefix}_{entry_idx}_bullet_{b_idx}",
        original_text=orig_text,
        injected_text=injected_text,
        injected_span=fake_num,
        expected_verdict="unsupported_claim",
        expected_detector="deterministic_p5",
    )
    return mut_resume, injection


def inject_inflated_verb(
    resume: TailoredResume,
    facts: CandidateFacts,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject verb scope inflation (L3) by replacing lead verb on a low-ceiling bullet."""
    rng = _stable_rng(seed, resume_id, "inflated_verb")
    mut_resume = copy.deepcopy(resume)

    matches = match_resume_bullets(resume, facts)
    facts_by_id = {f.id: f for f in facts.facts}

    # Find matches where matched fact scope_ceiling <= 2 and bullet has a lead verb
    eligible = [
        m for m in matches
        if m.fact_id is not None
        and m.fact_id in facts_by_id
        and facts_by_id[m.fact_id].scope_ceiling <= 2
    ]

    if not eligible:
        # Fallback: look for matches with ceiling <= 3
        eligible = [
            m for m in matches
            if m.fact_id is not None
            and m.fact_id in facts_by_id
            and facts_by_id[m.fact_id].scope_ceiling <= 3
        ]

    if not eligible:
        raise ValueError(f"Resume {resume_id} has no bullets with low scope ceiling for inflation.")

    chosen = eligible[rng.randrange(len(eligible))]
    ladder_match = extract_lead_verb(chosen.bullet)
    orig_lead_verb = ladder_match.phrase if ladder_match else chosen.bullet.split()[0]
    inflated_verb = INFLATION_VERBS[rng.randrange(len(INFLATION_VERBS))]

    # Replace lead verb
    injected_text = re.sub(
        rf"^{re.escape(orig_lead_verb)}\b",
        inflated_verb,
        chosen.bullet,
        flags=re.IGNORECASE,
    )
    if injected_text == chosen.bullet:
        injected_text = f"{inflated_verb} " + " ".join(chosen.bullet.split()[1:])

    # Apply replacement in resume
    found = False
    for exp_idx, exp in enumerate(mut_resume.experiences):
        for b_idx, b in enumerate(exp.bullets):
            if b == chosen.bullet:
                exp.bullets[b_idx] = injected_text
                found = True
                target_sec = f"experiences[{exp_idx}].bullets[{b_idx}]"
                bullet_id = f"exp_{exp_idx}_bullet_{b_idx}"
                break
        if found:
            break

    if not found:
        for proj_idx, proj in enumerate(mut_resume.projects):
            for b_idx, b in enumerate(proj.bullets):
                if b == chosen.bullet:
                    proj.bullets[b_idx] = injected_text
                    found = True
                    target_sec = f"projects[{proj_idx}].bullets[{b_idx}]"
                    bullet_id = f"proj_{proj_idx}_bullet_{b_idx}"
                    break
            if found:
                break

    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_L3_{seed}",
        resume_id=resume_id,
        defect_class="inflated_verb",
        target_section=target_sec,
        bullet_id=bullet_id,
        original_text=chosen.bullet,
        injected_text=injected_text,
        injected_span=inflated_verb,
        expected_verdict="inflated_scope",
        expected_detector="deterministic_p5",
    )
    return mut_resume, injection


def inject_fake_entity_date(
    resume: TailoredResume,
    profile: CandidateProfile,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject an unverified organization or altered period (L4)."""
    rng = _stable_rng(seed, resume_id, "fake_entity_date")
    mut_resume = copy.deepcopy(resume)

    if mut_resume.education:
        orig_inst = mut_resume.education[0].institution
        fake_inst = "Stanford University"
        mut_resume.education[0].institution = fake_inst
        injection = GroundTruthInjection(
            mutation_id=f"mut_{resume_id}_L4_{seed}",
            resume_id=resume_id,
            defect_class="fake_entity_date",
            target_section="education[0].institution",
            bullet_id="edu_0_inst",
            original_text=orig_inst,
            injected_text=fake_inst,
            injected_span=fake_inst,
            expected_verdict="unsupported_claim",
            expected_detector="deterministic_p5",
        )
        return mut_resume, injection

    if mut_resume.experiences:
        orig_org = mut_resume.experiences[0].organization
        fake_org = "Google DeepMind"
        mut_resume.experiences[0].organization = fake_org
        injection = GroundTruthInjection(
            mutation_id=f"mut_{resume_id}_L4_{seed}",
            resume_id=resume_id,
            defect_class="fake_entity_date",
            target_section="experiences[0].organization",
            bullet_id="exp_0_org",
            original_text=orig_org,
            injected_text=fake_org,
            injected_span=fake_org,
            expected_verdict="unsupported_claim",
            expected_detector="deterministic_p5",
        )
        return mut_resume, injection

    raise ValueError(f"Resume {resume_id} has no education or experiences to mutate entity.")


def inject_fabricated_responsibility_ablation(
    resume: TailoredResume,
    facts: CandidateFacts,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, CandidateFacts, GroundTruthInjection]:
    """Inject a fabricated responsibility (L5) via Evidence Ablation.

    Keeps genuine resume text unchanged, but deletes its supporting atomic fact
    from the facts collection seen by the judge. The claim becomes ungrounded by
    construction with natural phrasing.
    """
    rng = _stable_rng(seed, resume_id, "fabricated_responsibility_ablation")
    matches = match_resume_bullets(resume, facts)
    grounded_matches = [m for m in matches if m.fact_id is not None]

    if not grounded_matches:
        raise ValueError(f"Resume {resume_id} has no grounded bullets to ablate.")

    chosen = grounded_matches[rng.randrange(len(grounded_matches))]
    ablated_id = chosen.fact_id

    # Create new CandidateFacts with the ablated fact excluded
    new_facts_list = [f for f in facts.facts if f.id != ablated_id]
    active_facts = CandidateFacts(facts=new_facts_list)

    target_section = "bullets"
    bullet_id = "bullet_0"
    for exp_idx, exp in enumerate(resume.experiences):
        for b_idx, b in enumerate(exp.bullets):
            if b == chosen.bullet:
                target_section = f"experiences[{exp_idx}].bullets[{b_idx}]"
                bullet_id = f"exp_{exp_idx}_bullet_{b_idx}"
                break
    if target_section == "bullets":
        for proj_idx, proj in enumerate(resume.projects):
            for b_idx, b in enumerate(proj.bullets):
                if b == chosen.bullet:
                    target_section = f"projects[{proj_idx}].bullets[{b_idx}]"
                    bullet_id = f"proj_{proj_idx}_bullet_{b_idx}"
                    break

    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_L5_abl_{seed}",
        resume_id=resume_id,
        defect_class="fabricated_responsibility",
        target_section=target_section,
        bullet_id=bullet_id,
        original_text=chosen.bullet,
        injected_text=chosen.bullet,  # Wording is natural generator text
        injected_span=chosen.bullet,
        expected_verdict="unsupported_claim",
        expected_detector="claim_judge_llm",
        ablated_fact_id=ablated_id,
    )
    return resume, active_facts, injection


def inject_cross_project_conflation(
    resume: TailoredResume,
    facts: CandidateFacts,
    seed: int,
    resume_id: str,
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject cross-project conflation (L6) by splicing tools/metrics across distinct entries."""
    rng = _stable_rng(seed, resume_id, "cross_project_conflation")
    mut_resume = copy.deepcopy(resume)

    # Need at least two distinct experiences or projects
    all_entries: list[tuple[str, int, str, list[str]]] = []  # (kind, idx, name, bullets)
    for idx, exp in enumerate(mut_resume.experiences):
        if exp.bullets:
            all_entries.append(("experiences", idx, exp.organization, exp.bullets))
    for idx, proj in enumerate(mut_resume.projects):
        if proj.bullets:
            all_entries.append(("projects", idx, proj.name, proj.bullets))

    if len(all_entries) < 2:
        raise ValueError(f"Resume {resume_id} needs at least 2 entries for cross-project conflation.")

    src_idx = rng.randrange(len(all_entries))
    dst_idx = (src_idx + 1 + rng.randrange(len(all_entries) - 1)) % len(all_entries)

    src_kind, src_i, src_name, src_bullets = all_entries[src_idx]
    dst_kind, dst_i, dst_name, dst_bullets = all_entries[dst_idx]

    # Distinctive splicing tokens:
    splice_tokens = [
        ("CAN bus protocol and STM32 timers", "CAN bus protocol"),
        ("PyTorch spectral graph pooling layers", "spectral graph pooling"),
        ("Slurm cluster job orchestration scripts", "Slurm cluster"),
        ("Redis distributed worker queue broker", "Redis worker queue"),
    ]
    token_full, token_span = splice_tokens[rng.randrange(len(splice_tokens))]

    orig_bullet = dst_bullets[0]
    injected_bullet = f"{orig_bullet.rstrip('.')} using {token_full}."

    if dst_kind == "experiences":
        mut_resume.experiences[dst_i].bullets[0] = injected_bullet
    else:
        mut_resume.projects[dst_i].bullets[0] = injected_bullet

    b_prefix = "exp" if dst_kind == "experiences" else "proj"
    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_L6_{seed}",
        resume_id=resume_id,
        defect_class="cross_project_conflation",
        target_section=f"{dst_kind}[{dst_i}].bullets[0]",
        bullet_id=f"{b_prefix}_{dst_i}_bullet_0",
        original_text=orig_bullet,
        injected_text=injected_bullet,
        injected_span=token_span,
        expected_verdict="unsupported_claim",
        expected_detector="claim_judge_llm",
    )
    return mut_resume, injection


def inject_meta_word(
    resume: TailoredResume,
    seed: int = 42,
    resume_id: str = "resume",
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject a forbidden pipeline meta-word (B1) into free text (summary or bullet)."""
    meta_word = "verified"
    data = resume.model_dump()
    orig_text = data.get("objective_or_summary") or ""
    injected_text = f"Student with verified expertise: {orig_text}"
    data["objective_or_summary"] = injected_text
    mut_resume = TailoredResume.model_validate(data)

    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_meta_word_{seed}",
        resume_id=resume_id,
        defect_class="meta_word",
        target_section="objective_or_summary",
        bullet_id="summary",
        original_text=orig_text,
        injected_text=injected_text,
        injected_span=meta_word,
        expected_verdict="unsupported_claim",
        expected_detector="deterministic_p5",
    )
    return mut_resume, injection


def inject_job_phrase_echo(
    resume: TailoredResume,
    job: JobPosting,
    seed: int = 42,
    resume_id: str = "resume",
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject an ungrounded 3-gram echoed verbatim from job description (B2)."""
    echo_phrase = "lightweight neural networks"
    data = resume.model_dump()
    orig_text = data.get("objective_or_summary") or ""
    injected_text = f"{orig_text} Seeking to apply {echo_phrase}."
    data["objective_or_summary"] = injected_text
    mut_resume = TailoredResume.model_validate(data)

    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_job_echo_{seed}",
        resume_id=resume_id,
        defect_class="job_phrase_echo",
        target_section="objective_or_summary",
        bullet_id="summary",
        original_text=orig_text,
        injected_text=injected_text,
        injected_span=echo_phrase,
        expected_verdict="unsupported_claim",
        expected_detector="deterministic_p5",
    )
    return mut_resume, injection


def inject_fused_facts(
    resume: TailoredResume,
    seed: int = 42,
    resume_id: str = "resume",
) -> tuple[TailoredResume, GroundTruthInjection]:
    """Inject a fact-fused sentence combining distinct achievements (B3)."""
    fused_text = "Spearheaded creation of Data Science department and won Area of the Month."
    data = resume.model_dump()
    if data.get("experiences") and data["experiences"][0].get("bullets"):
        orig_text = data["experiences"][0]["bullets"][0]
        data["experiences"][0]["bullets"][0] = fused_text
        b_id = "exp_0_bullet_0"
        target_sec = "experiences[0].bullets[0]"
    else:
        orig_text = data.get("objective_or_summary") or ""
        data["objective_or_summary"] = fused_text
        b_id = "summary"
        target_sec = "objective_or_summary"

    mut_resume = TailoredResume.model_validate(data)
    injection = GroundTruthInjection(
        mutation_id=f"mut_{resume_id}_fused_facts_{seed}",
        resume_id=resume_id,
        defect_class="fused_facts",
        target_section=target_sec,
        bullet_id=b_id,
        original_text=orig_text,
        injected_text=fused_text,
        injected_span=fused_text,
        expected_verdict="unsupported_claim",
        expected_detector="deterministic_p5",
    )
    return mut_resume, injection


# ---------------------------------------------------------------------------
# High-Level Dataset Generator
# ---------------------------------------------------------------------------

def generate_corrupted_dataset(
    clean_resumes: dict[str, TailoredResume],
    profiles: dict[str, CandidateProfile],
    facts_map: dict[str, CandidateFacts],
    seed: int = 42,
) -> tuple[list[CorruptedResume], list[GroundTruthInjection]]:
    """Generate a balanced corrupted dataset across the 6 defect classes (L1–L6).

    Args:
        clean_resumes: Mapping of resume_id -> TailoredResume.
        profiles: Mapping of resume_id -> CandidateProfile.
        facts_map: Mapping of resume_id -> CandidateFacts.
        seed: Base random seed.

    Returns:
        tuple[list[CorruptedResume], list[GroundTruthInjection]]:
            List of corrupted resumes and the master injection ledger.
    """
    corrupted_list: list[CorruptedResume] = []
    ledger: list[GroundTruthInjection] = []

    # Sort keys for deterministic iteration
    sorted_ids = sorted(clean_resumes.keys())

    for r_id in sorted_ids:
        resume = clean_resumes[r_id]
        profile = profiles[r_id]
        facts = facts_map[r_id]
        truth = GroundTruth(profile, facts)

        # L1: fake_skill
        try:
            mut_r, inj = inject_fake_skill(resume, truth, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L1", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L2: fake_number
        try:
            mut_r, inj = inject_fake_number(resume, truth, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L2", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L3: inflated_verb
        try:
            mut_r, inj = inject_inflated_verb(resume, facts, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L3", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L4: fake_entity_date
        try:
            mut_r, inj = inject_fake_entity_date(resume, profile, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L4", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L5: fabricated_responsibility (Evidence Ablation)
        try:
            mut_r, act_facts, inj = inject_fabricated_responsibility_ablation(resume, facts, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L5", resume=mut_r, injections=[inj], active_facts=act_facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L6: cross_project_conflation
        try:
            mut_r, inj = inject_cross_project_conflation(resume, facts, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L6", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L7: meta_word
        try:
            mut_r, inj = inject_meta_word(resume, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L7", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L8: job_phrase_echo
        try:
            sample_job = JobPosting(title="Engineering Intern", company="TechCorp", raw_description="Requires lightweight neural networks.")
            mut_r, inj = inject_job_phrase_echo(resume, sample_job, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L8", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

        # L9: fused_facts
        try:
            mut_r, inj = inject_fused_facts(resume, seed, r_id)
            c = CorruptedResume(resume_id=f"{r_id}_L9", resume=mut_r, injections=[inj], active_facts=facts)
            corrupted_list.append(c)
            ledger.append(inj)
        except Exception:
            pass

    return corrupted_list, ledger
