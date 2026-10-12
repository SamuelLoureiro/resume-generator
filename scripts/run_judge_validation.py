"""Command-line runner for Phase P6 Judge Validation.

Governed by docs/research_plan.md (Section 6) and phase_p6_judge_validation_plan.md (v2).
Executes three-way evaluation across:
1. Deterministic verifier (src/verification/)
2. Atomic claim-level judge (src/evaluation/claim_judge.py)
3. Legacy Faithfulness evaluator (LlamaIndex)

Features:
- --dry-run flag: Validates datasets, runs offline deterministic checks,
  computes exact call estimates, and writes manifest without calling external APIs.
- Transport-layer quota guard: Aborts if max-calls limit is reached.
- Localized True Positive ledger attribution.
- Claim-level False Positive Rate with Wilson 95% confidence intervals.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.evaluation import EvaluationDataset
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.data.synthetic_profiles import get_synthetic_fresh_grad, get_synthetic_researcher
from src.evaluation.claim_judge import (
    CLAIM_JUDGE_PROMPT_VERSION,
    ClaimLevelJudge,
    ResumeEvaluationPayload,
)
from src.evaluation.injection import (
    CorruptedResume,
    GroundTruthInjection,
    generate_corrupted_dataset,
)
from src.generation.chain import build_fallback_tailored_resume, get_gemini_llm
from src.verification import parse_tex_resume, verify_resume
from src.verification.report import VerificationReport

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("judge_validation")


def wilson_score_interval(successes: int, trials: int, confidence: float = 0.95) -> tuple[float, float]:
    """Calculate the Wilson score confidence interval for a binomial proportion."""
    if trials == 0:
        return (0.0, 0.0)
    z = 1.95996 if confidence == 0.95 else 2.57583  # 95% or 99%
    p = successes / trials
    denominator = 1.0 + (z**2) / trials
    centre_adjusted_probability = p + (z**2) / (2.0 * trials)
    adjusted_std_dev = math.sqrt((p * (1.0 - p) + (z**2) / (4.0 * trials)) / trials)
    lower = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper = (centre_adjusted_probability + z * adjusted_std_dev) / denominator
    return (max(0.0, float(lower)), min(1.0, float(upper)))


def compute_file_sha256(path: Path) -> str:
    """Compute the SHA-256 hash of a file."""
    if not path.exists():
        return "not_found"
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def get_git_sha() -> str:
    """Return the current Git commit SHA."""
    try:
        out = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT)
        return out.decode("utf-8").strip()
    except Exception:
        return "unknown"


class QuotaGuard:
    """Safeguard tracking and limiting external API calls."""

    def __init__(self, max_calls: int, counter_file: Path | None = None) -> None:
        self.max_calls = max_calls
        self.counter_file = counter_file
        self.calls_made = 0

    def record_call(self) -> None:
        if self.calls_made >= self.max_calls:
            raise RuntimeError(
                f"API call budget exceeded: {self.calls_made} >= {self.max_calls}. Execution stopped."
            )
        self.calls_made += 1
        if self.counter_file:
            self.counter_file.write_text(str(self.calls_made), encoding="utf-8")


TRACK_BY_TEST_CASE: dict[str, str] = {
    "genai_rag_intern": "ai",
    "data_science_ml_intern": "data",
    "backend_python_intern": "backend",
    "swe_algorithms_intern": "core_swe",
    "data_engineering_intern": "data",
}


def load_clean_validation_dataset() -> tuple[
    dict[str, TailoredResume],
    dict[str, CandidateProfile],
    dict[str, CandidateFacts],
    dict[str, JobPosting],
    dict[str, str],
]:
    """Assemble and verify the 10 clean resumes representing ground truth."""
    clean_resumes: dict[str, TailoredResume] = {}
    profiles: dict[str, CandidateProfile] = {}
    facts_map: dict[str, CandidateFacts] = {}
    jobs_map: dict[str, JobPosting] = {}
    tracks_map: dict[str, str] = {}

    real_profile = CandidateProfile.from_yaml(PROJECT_ROOT / "data" / "candidate_profile.yaml")
    real_facts = load_candidate_facts(PROJECT_ROOT / "data" / "candidate_facts.yaml")

    synth_grad_profile, synth_grad_facts = get_synthetic_fresh_grad()
    synth_res_profile, synth_res_facts = get_synthetic_researcher()

    eval_dataset = EvaluationDataset.from_yaml(PROJECT_ROOT / "data" / "eval" / "evaluation_dataset.yaml")
    jobs_by_id = {tc.id: tc.to_job_posting() for tc in eval_dataset.test_cases}

    # 1. Real Amazon Good fixture
    amazon_tex = (PROJECT_ROOT / "tests" / "golden" / "fixtures" / "good_amazon_resume.tex").read_text(
        encoding="utf-8"
    )
    amazon_resume = parse_tex_resume(amazon_tex)
    amazon_job = jobs_by_id.get("swe_algorithms_intern", list(jobs_by_id.values())[0])

    clean_resumes["real_amazon_good"] = amazon_resume
    profiles["real_amazon_good"] = real_profile
    facts_map["real_amazon_good"] = real_facts
    jobs_map["real_amazon_good"] = amazon_job
    tracks_map["real_amazon_good"] = "ai"

    # 2. Real Candidate Fallbacks across 5 benchmark jobs
    for tc_id, job in jobs_by_id.items():
        r_id = f"real_fallback_{tc_id}"
        res = build_fallback_tailored_resume(real_profile, job, language="en")
        clean_resumes[r_id] = res
        profiles[r_id] = real_profile
        facts_map[r_id] = real_facts
        jobs_map[r_id] = job
        tracks_map[r_id] = TRACK_BY_TEST_CASE.get(tc_id, "backend")

    # 3. Synthetic Fresh Grad Fallbacks (2 jobs)
    for tc_id in ["swe_algorithms_intern", "backend_python_intern"]:
        if tc_id in jobs_by_id:
            job = jobs_by_id[tc_id]
            r_id = f"synth_grad_{tc_id}"
            res = build_fallback_tailored_resume(synth_grad_profile, job, language="en")
            clean_resumes[r_id] = res
            profiles[r_id] = synth_grad_profile
            facts_map[r_id] = synth_grad_facts
            jobs_map[r_id] = job
            tracks_map[r_id] = TRACK_BY_TEST_CASE.get(tc_id, "core_swe")

    # 4. Synthetic Academic Researcher Fallbacks (2 jobs)
    for tc_id in ["genai_rag_intern", "data_science_ml_intern"]:
        if tc_id in jobs_by_id:
            job = jobs_by_id[tc_id]
            r_id = f"synth_res_{tc_id}"
            res = build_fallback_tailored_resume(synth_res_profile, job, language="en")
            clean_resumes[r_id] = res
            profiles[r_id] = synth_res_profile
            facts_map[r_id] = synth_res_facts
            jobs_map[r_id] = job
            tracks_map[r_id] = TRACK_BY_TEST_CASE.get(tc_id, "ai")

    # Pre-verification assertion: All 10 must hard_pass
    for r_id, res in clean_resumes.items():
        prof = profiles[r_id]
        fcts = facts_map[r_id]
        jb = jobs_map[r_id]
        trk = tracks_map[r_id]
        rep = verify_resume(res, prof, fcts, job=jb, track=trk)
        if not rep.hard_pass:
            unsupported = [c.reason for c in rep.fabrication.unsupported]
            inflated = [i.reason for i in rep.inflation.inflated]
            format_fails = [f"{c.name}: {c.detail}" for c in rep.format.failed]
            raise RuntimeError(
                f"Clean resume '{r_id}' failed pre-verification gate!\n"
                f"Unsupported: {unsupported}\nInflated: {inflated}\nFormat: {format_fails}"
            )

    logger.info("Successfully assembled and pre-verified %d clean resumes.", len(clean_resumes))
    return clean_resumes, profiles, facts_map, jobs_map, tracks_map



def filter_balanced_corrupted_dataset(
    corrupted_list: list[CorruptedResume],
    full_matrix: bool = False,
) -> list[CorruptedResume]:
    """Select a quota-safe balanced subset of corrupted resumes."""
    if full_matrix:
        return corrupted_list

    # Quota-safe budget: 2 L1, 2 L2, 2 L3, 2 L4, 15 L5, 15 L6
    quota_targets = {
        "fake_skill": 2,
        "fake_number": 2,
        "inflated_verb": 2,
        "fake_entity_date": 2,
        "fabricated_responsibility": 15,
        "cross_project_conflation": 15,
    }
    counts: dict[str, int] = {k: 0 for k in quota_targets}
    selected: list[CorruptedResume] = []

    for c in corrupted_list:
        if not c.injections:
            continue
        d_class = c.injections[0].defect_class
        if counts[d_class] < quota_targets[d_class]:
            selected.append(c)
            counts[d_class] += 1

    return selected


def evaluate_deterministic(
    resumes: list[tuple[str, TailoredResume, CandidateProfile, CandidateFacts, JobPosting, str, GroundTruthInjection | None]],
) -> dict[str, Any]:
    """Run deterministic checks on resumes and verify localized true positives."""
    hits_by_class: dict[str, int] = {}
    total_by_class: dict[str, int] = {}
    clean_false_positives = 0
    clean_total = 0

    for r_id, res, prof, fcts, jb, trk, inj in resumes:
        rep = verify_resume(res, prof, fcts, job=jb, track=trk)
        if inj is None:
            # Clean resume
            clean_total += 1
            if not rep.hard_pass:
                clean_false_positives += 1
        else:
            # Corrupted resume
            d_class = inj.defect_class
            total_by_class[d_class] = total_by_class.get(d_class, 0) + 1
            hit = False

            if d_class == "fake_skill":
                hit = any(inj.injected_span.lower() in c.text.lower() for c in rep.fabrication.unsupported_of("a"))
            elif d_class == "fake_number":
                hit = any(inj.injected_span in c.text for c in rep.fabrication.unsupported_of("b"))
            elif d_class == "inflated_verb":
                hit = any(inj.injected_span.lower() == i.verb.lower() for i in rep.inflation.inflated)
            elif d_class == "fake_entity_date":
                hit = any(inj.injected_span.lower() in c.text.lower() for c in rep.fabrication.unsupported_of("c"))
            elif d_class in ("fabricated_responsibility", "cross_project_conflation"):
                hit = False  # Invisible to deterministic checks by design

            if hit:
                hits_by_class[d_class] = hits_by_class.get(d_class, 0) + 1

    return {
        "hits_by_class": hits_by_class,
        "total_by_class": total_by_class,
        "clean_false_positives": clean_false_positives,
        "clean_total": clean_total,
    }


def select_legacy_corrupted_subset(corrupted_list: list[CorruptedResume]) -> list[CorruptedResume]:
    """Select 10 corrupted resumes balanced across L1-L6 (2 L1, 2 L2, 2 L3, 2 L4, 1 L5, 1 L6)."""
    by_class: dict[str, list[CorruptedResume]] = {}
    for c in corrupted_list:
        if c.injections:
            cls = c.injections[0].defect_class
            by_class.setdefault(cls, []).append(c)

    chosen: list[CorruptedResume] = []
    for cls in ("fake_skill", "fake_number", "inflated_verb", "fake_entity_date"):
        chosen.extend(by_class.get(cls, [])[:2])
    chosen.extend(by_class.get("fabricated_responsibility", [])[:1])
    chosen.extend(by_class.get("cross_project_conflation", [])[:1])
    return chosen


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase P6 Judge Validation Benchmark.")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for deterministic lie injection.")
    parser.add_argument("--dry-run", action="store_true", help="Run offline without making external API calls.")
    parser.add_argument("--max-calls", type=int, default=85, help="Hard ceiling for external API calls.")
    parser.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "runs" / "E00_judge", help="Output directory.")
    parser.add_argument("--full-matrix", action="store_true", help="Execute full 120-call matrix instead of quota-safe tier.")
    parser.add_argument(
        "--evaluators",
        choices=["all", "deterministic", "claim_judge", "legacy"],
        default="all",
        help="Evaluator(s) to execute.",
    )
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    guard = QuotaGuard(max_calls=args.max_calls, counter_file=args.output_dir / "api_calls.count")

    logger.info("--- PHASE P6: JUDGE VALIDATION BENCHMARK ---")
    logger.info("Seed: %d | Dry-Run: %s | Max Calls: %d", args.seed, args.dry_run, args.max_calls)

    # 1. Assemble clean dataset
    clean_resumes, profiles, facts_map, jobs_map, tracks_map = load_clean_validation_dataset()

    # 2. Generate corrupted mutations
    all_corrupted, all_ledger = generate_corrupted_dataset(
        clean_resumes=clean_resumes,
        profiles=profiles,
        facts_map=facts_map,
        seed=args.seed,
    )
    selected_corrupted = filter_balanced_corrupted_dataset(all_corrupted, full_matrix=args.full_matrix)

    logger.info("Generated %d total corrupted instances; selected %d for evaluation.", len(all_corrupted), len(selected_corrupted))

    # Calculate planned API calls
    clean_count = len(clean_resumes)
    corrupted_count = len(selected_corrupted)
    claim_judge_calls = clean_count + corrupted_count
    legacy_calls = min(15, clean_count + corrupted_count) if args.evaluators in ("all", "legacy") else 0
    total_estimated_calls = claim_judge_calls + legacy_calls

    print("\n=======================================================")
    print("ESTIMATED API CALL PLAN (Budget Guard):")
    print(f"  Clean Resumes (FPR test):      {clean_count} calls")
    print(f"  Corrupted Resumes (Recall):    {corrupted_count} calls")
    print(f"  Claim-Level Judge Total:       {claim_judge_calls} calls (gemini-3.1-flash-lite)")
    print(f"  Legacy Evaluator Total:        {legacy_calls} calls")
    print(f"  TOTAL ESTIMATED API CALLS:     {total_estimated_calls} calls")
    print(f"  Hard Quota Ceiling (--max):    {args.max_calls} calls")
    print("=======================================================\n")

    if total_estimated_calls > args.max_calls:
        logger.error(
            "Estimated calls (%d) exceeds max-calls ceiling (%d). Aborting.",
            total_estimated_calls,
            args.max_calls,
        )
        sys.exit(1)

    # 3. Always run Deterministic Verifier offline (0 API calls)
    det_samples: list[tuple[str, TailoredResume, CandidateProfile, CandidateFacts, JobPosting, str, GroundTruthInjection | None]] = []
    for r_id, res in clean_resumes.items():
        det_samples.append((r_id, res, profiles[r_id], facts_map[r_id], jobs_map[r_id], tracks_map[r_id], None))
    for c in selected_corrupted:
        base_id = c.resume_id.rsplit("_", 1)[0]
        inj = c.injections[0] if c.injections else None
        det_samples.append((c.resume_id, c.resume, profiles[base_id], c.active_facts, jobs_map[base_id], tracks_map[base_id], inj))

    det_results = evaluate_deterministic(det_samples)
    logger.info("Deterministic verifier evaluation complete: 0 API calls made.")

    if args.dry_run or args.evaluators == "deterministic":
        logger.info("DRY-RUN completed successfully without opening external network sockets.")
        manifest = {
            "experiment_id": "E00_judge",
            "mode": "dry_run" if args.dry_run else "deterministic_only",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_sha": get_git_sha(),
            "judge_model": get_settings().judge_model,
            "judge_temperature": get_settings().judge_temperature,
            "judge_prompt_version": CLAIM_JUDGE_PROMPT_VERSION,
            "seed": args.seed,
            "clean_samples_count": clean_count,
            "corrupted_samples_count": corrupted_count,
            "total_api_calls_made": 0,
            "total_api_calls_planned": total_estimated_calls,
            "deterministic_results": det_results,
        }
        (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(f"\nDry-run manifest written to {args.output_dir / 'manifest.json'}")
        return

    # 4. Live Evaluation with ClaimLevelJudge (Requires active API key)
    logger.info("Beginning live LLM evaluations with model: %s", get_settings().judge_model)
    claim_judge = ClaimLevelJudge(cache_dir=args.output_dir / ".cache")

    # Track hits and false positives
    judge_hits_by_class: dict[str, int] = {}
    judge_total_by_class: dict[str, int] = {}
    clean_claims_evaluated = 0
    clean_claims_false_positives = 0
    clean_resumes_false_positives = 0

    # Evaluate clean resumes first (Early stopping guard)
    for r_id, res in clean_resumes.items():
        cached = claim_judge.is_cached(r_id, res, facts_map[r_id])
        if not cached:
            guard.record_call()
        facts = facts_map[r_id]
        payload = claim_judge.evaluate_resume(r_id, res, facts)

        resume_has_fp = False
        for claim in payload.claims:
            clean_claims_evaluated += 1
            if claim.verdict in ("unsupported_claim", "inflated_scope"):
                clean_claims_false_positives += 1
                resume_has_fp = True
        if resume_has_fp:
            clean_resumes_false_positives += 1
        if not cached:
            time.sleep(2.0)

    logger.info(
        "Clean resumes evaluated: Claim FPR = %d/%d (%.3f)",
        clean_claims_false_positives,
        clean_claims_evaluated,
        clean_claims_false_positives / max(1, clean_claims_evaluated),
    )

    # Evaluate corrupted resumes
    for c in selected_corrupted:
        cached = claim_judge.is_cached(c.resume_id, c.resume, c.active_facts)
        if not cached:
            guard.record_call()
        base_id = c.resume_id.rsplit("_", 1)[0]
        inj = c.injections[0]
        d_class = inj.defect_class
        judge_total_by_class[d_class] = judge_total_by_class.get(d_class, 0) + 1

        payload = claim_judge.evaluate_resume(c.resume_id, c.resume, c.active_facts)

        # Check localized hit on target bullet
        target_claims = payload.claims_for_bullet(inj.bullet_id)
        if not target_claims:
            norm_id = inj.bullet_id.replace("experiences_", "exp_").replace("projects_", "proj_")
            target_claims = payload.claims_for_bullet(norm_id)
        hit = False
        for tc in target_claims:
            if tc.verdict == inj.expected_verdict:
                # Check span alignment
                if inj.injected_span.lower() in tc.source_span.lower() or inj.injected_span.lower() in tc.rationale.lower():
                    hit = True
                    break
        if not hit and target_claims:
            # Fallback: if any claim on target bullet flagged unsupported/inflated
            if any(tc.verdict in ("unsupported_claim", "inflated_scope") for tc in target_claims):
                hit = True

        if hit:
            judge_hits_by_class[d_class] = judge_hits_by_class.get(d_class, 0) + 1

        # Non-injected bullets count toward clean claims true negatives
        for claim in payload.claims:
            if claim.bullet_id != inj.bullet_id:
                clean_claims_evaluated += 1
                if claim.verdict in ("unsupported_claim", "inflated_scope"):
                    clean_claims_false_positives += 1

        if not cached:
            time.sleep(2.0)

    # 5. Evaluate Legacy Faithfulness Evaluator (if enabled)
    legacy_results: dict[str, Any] = {}
    prev_results_path = args.output_dir / "results.json"
    if prev_results_path.exists():
        try:
            prev_data = json.loads(prev_results_path.read_text(encoding="utf-8"))
            if "legacy" in prev_data and prev_data["legacy"].get("clean_evaluated", 0) == 5:
                legacy_results = prev_data["legacy"]
                logger.info("Reusing completed legacy evaluation results from %s", prev_results_path)
        except Exception:
            pass

    if not legacy_results and args.evaluators in ("all", "legacy") and legacy_calls > 0:
        logger.info("Evaluating legacy FaithfulnessEvaluator on a 15-sample subset...")
        from llama_index.core.evaluation import FaithfulnessEvaluator
        from src.evaluation.benchmark import format_candidate_facts, format_resume_claims

        settings = get_settings()
        legacy_llm = get_gemini_llm(model_name=settings.judge_model, temperature=settings.judge_temperature)
        legacy_evaluator = FaithfulnessEvaluator(llm=legacy_llm)

        legacy_clean_subset = list(clean_resumes.items())[:5]
        legacy_clean_fps = 0
        for r_id, res in legacy_clean_subset:
            guard.record_call()
            prof = profiles[r_id]
            resp = format_resume_claims(res)
            ctx = [format_candidate_facts(prof)]
            try:
                eval_res = legacy_evaluator.evaluate(response=resp, contexts=ctx)
                if not eval_res.passing:
                    legacy_clean_fps += 1
            except Exception as exc:
                logger.warning("Legacy evaluator failed on clean resume %s: %s", r_id, exc)
            time.sleep(2.0)

        legacy_corrupted_subset = select_legacy_corrupted_subset(selected_corrupted)
        legacy_hits_by_class: dict[str, int] = {}
        legacy_total_by_class: dict[str, int] = {}
        for c in legacy_corrupted_subset:
            guard.record_call()
            base_id = c.resume_id.rsplit("_", 1)[0]
            prof = profiles[base_id]
            inj = c.injections[0]
            d_class = inj.defect_class
            legacy_total_by_class[d_class] = legacy_total_by_class.get(d_class, 0) + 1
            resp = format_resume_claims(c.resume)
            ctx = [format_candidate_facts(prof)]
            try:
                eval_res = legacy_evaluator.evaluate(response=resp, contexts=ctx)
                # If passing is False, the evaluator flagged an error (detected defect)
                if not eval_res.passing:
                    legacy_hits_by_class[d_class] = legacy_hits_by_class.get(d_class, 0) + 1
            except Exception as exc:
                logger.warning("Legacy evaluator failed on corrupted resume %s: %s", c.resume_id, exc)
            time.sleep(2.0)

        legacy_results = {
            "clean_evaluated": len(legacy_clean_subset),
            "clean_false_positives": legacy_clean_fps,
            "hits_by_class": legacy_hits_by_class,
            "total_by_class": legacy_total_by_class,
        }

    # Compute Final Statistics
    claim_fpr = clean_claims_false_positives / max(1, clean_claims_evaluated)
    claim_fpr_ci = wilson_score_interval(clean_claims_false_positives, clean_claims_evaluated)
    resume_fpr = clean_resumes_false_positives / max(1, clean_count)

    results_summary = {
        "clean_claims_evaluated": clean_claims_evaluated,
        "clean_claims_false_positives": clean_claims_false_positives,
        "claim_fpr": round(claim_fpr, 4),
        "claim_fpr_wilson_ci": [round(claim_fpr_ci[0], 4), round(claim_fpr_ci[1], 4)],
        "clean_resumes_evaluated": clean_count,
        "clean_resumes_false_positives": clean_resumes_false_positives,
        "resume_fpr": round(resume_fpr, 4),
        "deterministic": det_results,
        "claim_judge": {
            "hits_by_class": judge_hits_by_class,
            "total_by_class": judge_total_by_class,
        },
        "legacy": legacy_results,
    }

    (args.output_dir / "results.json").write_text(json.dumps(results_summary, indent=2), encoding="utf-8")

    manifest = {
        "experiment_id": "E00_judge",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "git_sha": get_git_sha(),
        "judge_model": get_settings().judge_model,
        "judge_temperature": get_settings().judge_temperature,
        "judge_prompt_version": CLAIM_JUDGE_PROMPT_VERSION,
        "seed": args.seed,
        "clean_resumes_count": clean_count,
        "corrupted_resumes_count": corrupted_count,
        "clean_claims_count": clean_claims_evaluated,
        "total_api_calls_made": guard.calls_made,
        "api_budget_cap": args.max_calls,
        "dataset_hashes": {
            "candidate_profile": compute_file_sha256(PROJECT_ROOT / "data" / "candidate_profile.yaml"),
            "candidate_facts": compute_file_sha256(PROJECT_ROOT / "data" / "candidate_facts.yaml"),
            "evaluation_dataset": compute_file_sha256(PROJECT_ROOT / "data" / "eval" / "evaluation_dataset.yaml"),
        },
        "results": results_summary,
    }
    (args.output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    logger.info("Validation complete! Manifest and results saved to %s", args.output_dir)

    print("\n" + "=" * 80)
    print("PHASE P6 BENCHMARK RESULTS SUMMARY:")
    print("=" * 80)
    print(f"Total API Calls Made: {guard.calls_made} / {args.max_calls}")
    print(f"Claim-level FPR: {results_summary['claim_fpr']:.2%} (Wilson 95% CI: [{results_summary['claim_fpr_wilson_ci'][0]:.2%}, {results_summary['claim_fpr_wilson_ci'][1]:.2%}])")
    print(f"Resume-level FPR: {results_summary['resume_fpr']:.2%}")
    print("\nRecall by Defect Class:")
    classes = ["fake_skill", "fake_number", "inflated_verb", "fake_entity_date", "fabricated_responsibility", "cross_project_conflation"]
    print(f"{'Class':<28} | {'Deterministic':<15} | {'Claim Judge':<15} | {'Legacy Evaluator':<15}")
    print("-" * 80)
    for c in classes:
        det_h = det_results['hits_by_class'].get(c, 0)
        det_t = det_results['total_by_class'].get(c, 0)
        det_str = f"{det_h}/{det_t}" if det_t > 0 else "N/A"

        cj_h = judge_hits_by_class.get(c, 0)
        cj_t = judge_total_by_class.get(c, 0)
        cj_str = f"{cj_h}/{cj_t}" if cj_t > 0 else "N/A"

        leg_h = legacy_results.get("hits_by_class", {}).get(c, 0)
        leg_t = legacy_results.get("total_by_class", {}).get(c, 0)
        leg_str = f"{leg_h}/{leg_t}" if leg_t > 0 else "N/A"

        print(f"{c:<28} | {det_str:<15} | {cj_str:<15} | {leg_str:<15}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
