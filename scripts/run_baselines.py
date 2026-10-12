"""Command-line runner for Phase P7 Baselines (B0, B1, B3).

Governed by docs/research_plan.md (Sections 4, 5, 7) and docs/agent_prompts.md.
Evaluates three baseline generation variants across the dev benchmark suite:
1. B0: Deterministic fallback (no LLM, no RAG)
2. B1: Current pipeline (Hybrid RAG + Gemini LLM)
3. B3: Full knowledge base baseline (no retrieval, full KB in prompt + Gemini LLM)

Outputs:
- runs/E01_baselines/manifest.json (reproducibility metadata & quota tracking)
- runs/E01_baselines/results.json (raw per-job and aggregate metric scores)
- runs/E01_baselines/resumes/ (compiled LaTeX and PDF artifacts)
- docs/experiments/E01_baselines.md (benchmark results tables; human writes Interpretation/Conclusions)
"""

from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import logging
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.evaluation import EvaluationDataset, EvaluationTestCase
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.evaluation.claim_judge import (
    CLAIM_JUDGE_PROMPT_VERSION,
    ClaimLevelJudge,
    ResumeEvaluationPayload,
)
from src.generation.chain import ResumeGenerationChain, get_gemini_llm
from src.generation.formatter import ResumeFormatter
from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.b1_hybrid_rag import generate_b1
from src.generation.variants.b3_full_context import (
    generate_b3,
    load_full_knowledge_base_context,
)
from src.retrieval.pipeline import KnowledgeBasePipeline
from src.verification import parse_tex_resume
from src.verification.report import VerificationReport, verify_resume

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("baselines_runner")


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
    """Enforces strict safety budget on LLM API calls."""

    def __init__(self, max_calls: int) -> None:
        self.max_calls = max_calls
        self.calls_by_model: dict[str, int] = {}
        self.total_calls = 0

    def record_call(self, model_id: str) -> None:
        if self.total_calls >= self.max_calls:
            raise RuntimeError(
                f"API call budget exceeded: {self.total_calls} >= {self.max_calls}. Runner halted."
            )
        self.total_calls += 1
        self.calls_by_model[model_id] = self.calls_by_model.get(model_id, 0) + 1


def compile_and_verify(
    resume: TailoredResume,
    candidate: CandidateProfile,
    facts: CandidateFacts,
    test_case: EvaluationTestCase,
    variant_id: str,
    formatter: ResumeFormatter,
    resumes_dir: Path,
    judge: ClaimLevelJudge | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Render, compile, and run deterministic and claim-level metrics on one resume."""
    job_posting = test_case.to_job_posting()
    filename_stem = f"{variant_id}_{test_case.id}"

    # 1. Render LaTeX
    tex_str = formatter.render_latex(resume)
    tex_path = resumes_dir / f"{filename_stem}.tex"
    tex_path.write_text(tex_str, encoding="utf-8")

    # 2. Compile to PDF via Tectonic
    pdf_path: Path | None = None
    try:
        pdf_path = formatter.compile_pdf(
            resume,
            output_filename=f"{filename_stem}.pdf",
            keep_tex=True,
        )
        # Move or symlink into resumes_dir if not placed there directly
        target_pdf = resumes_dir / f"{filename_stem}.pdf"
        if pdf_path.exists() and pdf_path != target_pdf:
            pdf_path.replace(target_pdf)
            pdf_path = target_pdf
    except Exception as exc:
        logger.warning("PDF compilation failed for %s: %s", filename_stem, exc)
        pdf_path = None

    # 3. Deterministic Verification (M1a-c, M2, M3, M4, M5)
    report: VerificationReport = verify_resume(
        resume=resume,
        profile=candidate,
        facts=facts,
        job=job_posting,
        track=test_case.target_track,
        tex=tex_str,
        pdf_path=pdf_path,
    )

    # 4. Claim-Level Judge (M1d)
    judge_payload: ResumeEvaluationPayload | None = None
    unsupported_claim_count = 0
    inflated_claim_count = 0
    total_claims = 0

    if judge is not None and not dry_run:
        try:
            judge_payload = judge.evaluate_resume(resume_id=filename_stem, resume=resume, facts=facts)
            total_claims = len(judge_payload.claims)
            unsupported_claim_count = sum(
                1 for v in judge_payload.claims if v.verdict == "unsupported_claim"
            )
            inflated_claim_count = sum(
                1 for v in judge_payload.claims if v.verdict == "inflated_scope"
            )
        except Exception as exc:
            logger.error("Claim judge failed for %s: %s", filename_stem, exc)

    # Hard-Pass Definition:
    # 0 fabrication (M1a-c == 0 and M1d == 0), 0 inflation (M2 == 0 and M1d_inflated == 0),
    # no fabricated keywords (M4), and all M5 format checks passed.
    has_deterministic_fab = bool(report.fabrication.unsupported)
    has_claim_fab = unsupported_claim_count > 0
    has_deterministic_inf = bool(report.inflation.inflated)
    has_claim_inf = inflated_claim_count > 0
    has_kw_fab = bool(report.keywords and report.keywords.fabricated)
    format_passed = report.format.all_passed

    hard_pass = (
        not has_deterministic_fab
        and not has_claim_fab
        and not has_deterministic_inf
        and not has_claim_inf
        and not has_kw_fab
        and format_passed
    )

    return {
        "variant": variant_id,
        "job_id": test_case.id,
        "title": test_case.title,
        "company": test_case.company,
        "language": test_case.language,
        "track": test_case.target_track,
        "hard_pass": hard_pass,
        "m1_unsupported_tools": [c.text for c in report.fabrication.unsupported_of("a")],
        "m1_unsupported_metrics": [c.text for c in report.fabrication.unsupported_of("b")],
        "m1_unsupported_timeline": [c.text for c in report.fabrication.unsupported_of("c")],
        "m1_deterministic_unsupported_count": len(report.fabrication.unsupported),
        "m1d_unsupported_claims_count": unsupported_claim_count,
        "m1d_total_claims": total_claims,
        "m2_inflated_verbs_count": len(report.inflation.inflated),
        "m2_unmatched_bullets_count": len(report.inflation.unmatched),
        "m2_assessed_bullets_count": report.inflation.assessed,
        "m2_inflation_rate": report.inflation.rate or 0.0,
        "m3_coverage": report.coverage.coverage or 0.0 if report.coverage else 0.0,
        "m3_matched_facts": len(report.coverage.covered) if report.coverage else 0,
        "m3_relevant_facts": len(report.coverage.relevant) if report.coverage else 0,
        "m4_truthful_keywords": report.keywords.alignment or 0.0 if report.keywords else 0.0,
        "m4_fabricated_keywords": list(report.keywords.fabricated) if report.keywords else [],
        "m5_format_passed": format_passed,
        "m5_failed_checks": [c.name for c in report.format.failed],
        "pdf_compiled": pdf_path is not None,
    }


def generate_markdown_report(
    summary_by_variant: dict[str, dict[str, Any]],
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
) -> str:
    """Generate Markdown report for docs/experiments/E01_baselines.md."""
    lines: list[str] = [
        "# Experiment E01 — Baselines Benchmark (B0, B1, B3)",
        "",
        "> Governed by `docs/research_plan.md` (Sections 4, 5, 7).",
        "> Evaluates the reference baselines B0 (Deterministic fallback), B1 (Hybrid RAG), and B3 (Full-Context) across the 7 development internship postings.",
        "",
        "## Experiment Metadata",
        "",
        f"- **Date:** {manifest['timestamp']}",
        f"- **Git SHA:** `{manifest['git_sha']}`",
        f"- **Dataset Manifest SHA-256:** `{manifest['dataset_manifest_sha256']}`",
        f"- **Generator Model:** `{manifest['generator_model']}`",
        f"- **Judge Model:** `{manifest['judge_model']}`",
        f"- **Judge Prompt Version:** `{manifest['judge_prompt_version']}`",
        f"- **Total API Calls Made:** {manifest['total_api_calls']}",
        f"  - Generator calls: {manifest['api_calls_breakdown'].get(manifest['generator_model'], 0)}",
        f"  - Judge calls: {manifest['api_calls_breakdown'].get(manifest['judge_model'], 0)}",
        "",
        "## Headline Metrics Summary",
        "",
        "| Variant | Description | Hard-Pass Rate | M1 Fabrication (Det + Judge) | M2 Inflation Rate | M3 Coverage | M4 Truthful KW | M5 Format Pass |",
        "|---|---|---|---|---|---|---|---|",
    ]

    for v_id, summary in summary_by_variant.items():
        n = summary["n"]
        hp_pct = (summary["hard_pass_count"] / n) * 100 if n else 0
        m1_avg = summary["m1_total_unsupported"] / n if n else 0
        m2_avg = (summary["m2_total_inflated"] / summary["m2_total_assessed"] * 100) if summary["m2_total_assessed"] else 0
        m3_avg = (summary["m3_sum"] / n) * 100 if n else 0
        m4_avg = (summary["m4_sum"] / n) * 100 if n else 0
        m5_pct = (summary["m5_passed_count"] / n) * 100 if n else 0

        desc = {
            "b0": "Deterministic Fallback (No LLM)",
            "b1": "Hybrid RAG Pipeline (Gemini)",
            "b3": "Full Knowledge Base in Prompt (Gemini)",
        }.get(v_id, v_id)

        lines.append(
            f"| **{v_id.upper()}** | {desc} | **{hp_pct:.1f}%** ({summary['hard_pass_count']}/{n}) | {m1_avg:.2f} claims/res | {m2_avg:.1f}% | {m3_avg:.1f}% | {m4_avg:.1f}% | {m5_pct:.1f}% ({summary['m5_passed_count']}/{n}) |"
        )

    lines.extend([
        "",
        "## Per-Posting Results",
        "",
        "| Variant | Job ID | Language | Track | Hard Pass | M1 Det (Tools/Num/Dates) | M1d Claims | M2 Inflated | M3 Coverage | M4 KW | M5 Format |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ])

    for r in results:
        hp_str = "✅ PASS" if r["hard_pass"] else "❌ FAIL"
        det_m1 = f"{len(r['m1_unsupported_tools'])}/{len(r['m1_unsupported_metrics'])}/{len(r['m1_unsupported_timeline'])}"
        m1d_str = f"{r['m1d_unsupported_claims_count']}/{r['m1d_total_claims']}"
        m2_str = f"{r['m2_inflated_verbs_count']}/{r['m2_assessed_bullets_count']}"
        m3_str = f"{r['m3_coverage']*100:.0f}%"
        m4_str = f"{r['m4_truthful_keywords']*100:.0f}%"
        m5_str = "PASS" if r["m5_format_passed"] else f"FAIL ({', '.join(r['m5_failed_checks'])})"

        lines.append(
            f"| `{r['variant']}` | `{r['job_id']}` | `{r['language']}` | `{r['track']}` | {hp_str} | {det_m1} | {m1d_str} | {m2_str} | {m3_str} | {m4_str} | {m5_str} |"
        )

    lines.extend([
        "",
        "## Execution Commands",
        "",
        "```bash",
        "# Dry run (offline check)",
        "python3 scripts/run_baselines.py --dry-run",
        "",
        "# Live execution of all baselines",
        "python3 scripts/run_baselines.py --variants b0,b1,b3 --max-calls 100",
        "```",
        "",
        "## Interpretation",
        "<!-- Written by the human author (Rule ADR-006 / GEMINI.md) -->",
        "",
        "## Conclusions",
        "<!-- Written by the human author (Rule ADR-006 / GEMINI.md) -->",
        "",
    ])

    return "\n".join(lines)


def run_baselines(
    dev_dir: Path,
    variants: list[str],
    output_dir: Path,
    dry_run: bool,
    max_calls: int,
    seed: int,
) -> None:
    """Execute the Phase P7 Baselines benchmark."""
    settings = get_settings()
    resumes_dir = output_dir / "resumes"
    resumes_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load ground truth candidate profile and facts
    candidate = CandidateProfile.from_yaml(PROJECT_ROOT / "data" / "candidate_profile.yaml")
    facts = load_candidate_facts(PROJECT_ROOT / "data" / "candidate_facts.yaml")
    manifest_sha256 = compute_file_sha256(PROJECT_ROOT / "data" / "eval" / "MANIFEST.sha256")
    git_sha = get_git_sha()

    # 2. Load evaluation test cases
    dataset = EvaluationDataset.from_directory(dev_dir)
    logger.info("Loaded %d test cases from %s", len(dataset), dev_dir)

    # 3. Quota estimation and planning
    num_jobs = len(dataset)
    est_gen_calls = 0
    if "b1" in variants:
        est_gen_calls += num_jobs
    if "b3" in variants:
        est_gen_calls += num_jobs

    est_judge_calls = len(variants) * num_jobs
    est_total_calls = est_gen_calls + est_judge_calls

    print("\n" + "=" * 70)
    print("📊 PHASE P7 BASELINES EXECUTION PLAN")
    print("=" * 70)
    print(f"Test cases (dev jobs): {num_jobs}")
    print(f"Selected variants:     {', '.join(variants)}")
    print(f"Generator model:       {settings.generation_model}")
    print(f"Judge model:           {settings.judge_model}")
    print(f"Estimated LLM calls:   {est_total_calls} (Gen: {est_gen_calls}, Judge: {est_judge_calls})")
    print(f"Safety call budget:    {max_calls}")
    print(f"Dry run mode:          {dry_run}")
    print("=" * 70 + "\n")

    if dry_run:
        logger.info("Executing dry run: running B0 offline, testing compilation & verification...")
        # For dry-run, run B0 locally to test all test cases without any API calls
        formatter = ResumeFormatter(output_dir=resumes_dir)
        dry_results: list[dict[str, Any]] = []
        for tc in dataset:
            resume = generate_b0(candidate=candidate, job=tc.to_job_posting(), language=tc.language)
            res_dict = compile_and_verify(
                resume=resume,
                candidate=candidate,
                facts=facts,
                test_case=tc,
                variant_id="b0_dry",
                formatter=formatter,
                resumes_dir=resumes_dir,
                judge=None,
                dry_run=True,
            )
            dry_results.append(res_dict)

        print("\n✅ Dry run completed successfully! All 7 postings compile and verify offline.")
        print(f"Pass count: {sum(1 for r in dry_results if r['hard_pass'])}/{len(dry_results)}")
        return

    # Real run
    quota_guard = QuotaGuard(max_calls=max_calls)
    formatter = ResumeFormatter(output_dir=resumes_dir)

    # Initialize models
    gen_llm = get_gemini_llm(model_name=settings.generation_model, temperature=0.0)
    judge_llm = get_gemini_llm(model_name=settings.judge_model, temperature=0.0)

    class MonitoredLLM:
        def __init__(self, target_llm: Any, model_id: str, guard: QuotaGuard) -> None:
            self._target = target_llm
            self._model_id = model_id
            self._guard = guard

        def chat(self, messages: Any) -> Any:
            self._guard.record_call(self._model_id)
            return self._target.chat(messages)

        def complete(self, prompt: str) -> Any:
            self._guard.record_call(self._model_id)
            return self._target.complete(prompt)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._target, name)

    monitored_gen_llm = MonitoredLLM(gen_llm, settings.generation_model, quota_guard)
    monitored_judge_llm = MonitoredLLM(judge_llm, settings.judge_model, quota_guard)

    judge = ClaimLevelJudge(llm=monitored_judge_llm, cache_dir=cache_dir)
    chain = ResumeGenerationChain(llm=monitored_gen_llm)

    # Pre-setup pipeline for B1 and context for B3
    pipeline = KnowledgeBasePipeline() if "b1" in variants else None
    if pipeline:
        pipeline.setup()

    full_kb_context = load_full_knowledge_base_context() if "b3" in variants else ""

    all_results: list[dict[str, Any]] = []

    for variant_id in variants:
        logger.info("=== Running Variant: %s ===", variant_id.upper())
        for tc in dataset:
            job_posting = tc.to_job_posting()
            logger.info("Variant %s -> Job: %s (%s)", variant_id.upper(), tc.id, tc.company)

            filename_stem = f"{variant_id}_{tc.id}"
            existing_tex = resumes_dir / f"{filename_stem}.tex"
            if existing_tex.exists():
                logger.info("Loading previously generated resume from %s", existing_tex)
                resume = parse_tex_resume(existing_tex.read_text(encoding="utf-8"))
            elif variant_id == "b0":
                resume = generate_b0(candidate=candidate, job=job_posting, language=tc.language)
            elif variant_id == "b1":
                assert pipeline is not None
                resume, _ = generate_b1(
                    candidate=candidate,
                    job=job_posting,
                    pipeline=pipeline,
                    chain=chain,
                    language=tc.language,
                )
            elif variant_id == "b3":
                resume, _ = generate_b3(
                    candidate=candidate,
                    job=job_posting,
                    chain=chain,
                    full_kb_context=full_kb_context,
                    language=tc.language,
                )
            else:
                raise ValueError(f"Unknown variant: {variant_id}")

            res_dict = compile_and_verify(
                resume=resume,
                candidate=candidate,
                facts=facts,
                test_case=tc,
                variant_id=variant_id,
                formatter=formatter,
                resumes_dir=resumes_dir,
                judge=judge,
                dry_run=False,
            )
            all_results.append(res_dict)
            time.sleep(2.5)

    # Compute summary by variant
    summary_by_variant: dict[str, dict[str, Any]] = {}
    for v_id in variants:
        v_results = [r for r in all_results if r["variant"] == v_id]
        n = len(v_results)
        summary_by_variant[v_id] = {
            "n": n,
            "hard_pass_count": sum(1 for r in v_results if r["hard_pass"]),
            "m1_total_unsupported": sum(
                r["m1_deterministic_unsupported_count"] + r["m1d_unsupported_claims_count"]
                for r in v_results
            ),
            "m2_total_inflated": sum(r["m2_inflated_verbs_count"] for r in v_results),
            "m2_total_assessed": sum(r["m2_assessed_bullets_count"] for r in v_results),
            "m3_sum": sum(r["m3_coverage"] for r in v_results),
            "m4_sum": sum(r["m4_truthful_keywords"] for r in v_results),
            "m5_passed_count": sum(1 for r in v_results if r["m5_format_passed"]),
        }

    manifest = {
        "timestamp": datetime.now().isoformat(),
        "git_sha": git_sha,
        "dataset_manifest_sha256": manifest_sha256,
        "variants": variants,
        "generator_model": settings.generation_model,
        "judge_model": settings.judge_model,
        "judge_prompt_version": CLAIM_JUDGE_PROMPT_VERSION,
        "total_api_calls": quota_guard.total_calls,
        "api_calls_breakdown": quota_guard.calls_by_model,
        "seed": seed,
    }

    # Write output files
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "results.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")

    report_md = generate_markdown_report(summary_by_variant, all_results, manifest)
    report_path = PROJECT_ROOT / "docs" / "experiments" / "E01_baselines.md"
    report_path.write_text(report_md, encoding="utf-8")

    logger.info("Baselines benchmark completed successfully!")
    logger.info("Results saved to %s and %s", output_dir, report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase P7 Baselines benchmark.")
    parser.add_argument(
        "--dev-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "dev",
        help="Path to development job postings directory",
    )
    parser.add_argument(
        "--variants",
        type=str,
        default="b0,b1,b3",
        help="Comma-separated variants to execute (e.g. b0,b1,b3)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "runs" / "E01_baselines",
        help="Directory to save run manifests, outputs, and cache",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run deterministic offline checks without making API calls",
    )
    parser.add_argument(
        "--max-calls",
        type=int,
        default=100,
        help="Strict upper bound on external API calls",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )

    args = parser.parse_args()
    selected_variants = [v.strip().lower() for v in args.variants.split(",") if v.strip()]

    run_baselines(
        dev_dir=args.dev_dir,
        variants=selected_variants,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        max_calls=args.max_calls,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
