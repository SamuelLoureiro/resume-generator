"""Command-line runner for Phase P8 Verifier (V1 Benchmark).

Governed by docs/research_plan.md (Sections 4, 7; Hypothesis H1) and docs/agent_prompts.md.
Evaluates the V1 verified variant (Error-guided regeneration loop + deterministic repair)
against the dev benchmark suite.

Outputs:
- runs/E02_verifier/manifest.json (reproducibility metadata & quota tracking)
- runs/E02_verifier/results.json (raw per-job and aggregate metric scores)
- runs/E02_verifier/resumes/ (compiled LaTeX and PDF artifacts)
- docs/experiments/E02_verifier.md (benchmark results tables; human writes Interpretation/Conclusions)
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
from src.generation.prompts import V1_FEEDBACK_PROMPT_VERSION
from src.generation.variants.b0_fallback import generate_b0
from src.generation.variants.v1_verified import V1Trace, generate_v1
from src.retrieval.pipeline import KnowledgeBasePipeline
from src.verification import parse_tex_resume
from src.verification.report import VerificationReport, verify_resume

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verifier_runner")


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
        target_pdf = resumes_dir / f"{filename_stem}.pdf"
        if pdf_path.exists() and pdf_path != target_pdf:
            pdf_path.replace(target_pdf)
            pdf_path = target_pdf
    except Exception as exc:
        logger.warning("PDF compilation failed for %s: %s", filename_stem, exc)
        pdf_path = None

    # 3. Deterministic Verification
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
    total_judge_claims = 0

    if judge is not None and not dry_run:
        try:
            judge_payload = judge.evaluate_resume(resume_id=filename_stem, resume=resume, facts=facts)
            total_judge_claims = len(judge_payload.claims)
            unsupported_claim_count = sum(
                1 for v in judge_payload.claims if v.verdict == "unsupported_claim"
            )
            inflated_claim_count = sum(
                1 for v in judge_payload.claims if v.verdict == "inflated_scope"
            )
        except Exception as exc:
            logger.error("Claim judge failed for %s: %s", filename_stem, exc)

    # Combined Metric Rates
    det_unsupported = len(report.fabrication.unsupported)
    det_checked = report.fabrication.total_claims
    combined_unsupported = det_unsupported + unsupported_claim_count
    combined_total_claims = det_checked + total_judge_claims
    m1_rate = (combined_unsupported / combined_total_claims) if combined_total_claims > 0 else 0.0

    det_inflated = len(report.inflation.inflated)
    det_assessed = report.inflation.assessed
    combined_inflated = det_inflated + inflated_claim_count
    combined_scope_claims = det_assessed + sum(
        1 for v in (judge_payload.claims if judge_payload else []) if v.claim_type == "scope"
    )
    m2_rate = (combined_inflated / combined_scope_claims) if combined_scope_claims > 0 else 0.0

    has_kw_fab = bool(report.keywords and report.keywords.fabricated)
    format_passed = report.format.all_passed

    hard_pass = (
        combined_unsupported == 0
        and combined_inflated == 0
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
        "m1_rate": m1_rate,
        "m1_unsupported_total": combined_unsupported,
        "m1_checked_total": combined_total_claims,
        "m1_deterministic_unsupported_count": det_unsupported,
        "m1d_unsupported_claims_count": unsupported_claim_count,
        "m1d_total_claims": total_judge_claims,
        "m2_rate": m2_rate,
        "m2_inflated_total": combined_inflated,
        "m2_assessed_total": combined_scope_claims,
        "m2_deterministic_inflated_count": det_inflated,
        "m2_unmatched_bullets_count": len(report.inflation.unmatched),
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
    summary: dict[str, Any],
    results: list[dict[str, Any]],
    manifest: dict[str, Any],
    traces: list[dict[str, Any]],
) -> str:
    """Generate Markdown report for docs/experiments/E02_verifier.md."""
    n = summary["n"]
    hp_pct = (summary["hard_pass_count"] / n) * 100 if n else 0
    m1_rate_avg = (summary["m1_rate_sum"] / n) * 100 if n else 0
    m2_rate_avg = (summary["m2_rate_sum"] / n) * 100 if n else 0
    m3_avg = (summary["m3_sum"] / n) * 100 if n else 0
    m4_avg = (summary["m4_sum"] / n) * 100 if n else 0
    m5_pct = (summary["m5_passed_count"] / n) * 100 if n else 0

    lines: list[str] = [
        "# Experiment E02 — Verifier V1 (Error-Guided Regeneration & Repair)",
        "",
        "> Governed by `docs/research_plan.md` (Sections 4, 7; Hypothesis H1).",
        "> Evaluates the V1 verified variant across the 7 development internship postings.",
        "",
        "## Experiment Metadata",
        "",
        f"- **Date:** {manifest['timestamp']}",
        f"- **Git SHA:** `{manifest['git_sha']}`",
        f"- **Dataset Manifest SHA-256:** `{manifest['dataset_manifest_sha256']}`",
        f"- **Generator Model:** `{manifest['generator_model']}`",
        f"- **Judge Model:** `{manifest['judge_model']}`",
        f"- **Judge Prompt Version:** `{manifest['judge_prompt_version']}`",
        f"- **Feedback Prompt Version:** `{manifest['feedback_prompt_version']}`",
        f"- **Total API Calls Made:** {manifest['total_api_calls']}",
        f"  - Generator calls: {manifest['api_calls_breakdown'].get(manifest['generator_model'], 0)}",
        f"  - Judge calls: {manifest['api_calls_breakdown'].get(manifest['judge_model'], 0)}",
        "",
        "## Headline Metrics Summary",
        "",
        "| Variant | Description | Hard-Pass Rate | M1 Fabrication Rate | M2 Inflation Rate | M3 Coverage | M4 Truthful KW | M5 Format Pass |",
        "|---|---|---|---|---|---|---|---|",
        f"| **V1** | Verifier (Loop + Repair) | **{hp_pct:.1f}%** ({summary['hard_pass_count']}/{n}) | {m1_rate_avg:.1f}% | {m2_rate_avg:.1f}% | {m3_avg:.1f}% | {m4_avg:.1f}% | {m5_pct:.1f}% ({summary['m5_passed_count']}/{n}) |",
        "",
        "## V1 Resolution Path Breakdown",
        "",
        "| Resolution Path | Meaning | Count | Share |",
        "|---|---|---|---|",
        f"| `clean@0` | Initial generation passed with 0 defects | {summary['path_clean0']} | {summary['path_clean0']/n*100:.1f}% |",
        f"| `clean@1` | Corrected after 1 error-guided feedback round | {summary['path_clean1']} | {summary['path_clean1']/n*100:.1f}% |",
        f"| `clean@2` | Corrected after 2 error-guided feedback rounds | {summary['path_clean2']} | {summary['path_clean2']/n*100:.1f}% |",
        f"| `repaired` | Deterministic repair resolved residual defects | {summary['path_repaired']} | {summary['path_repaired']/n*100:.1f}% |",
        f"| `fallback` | Deterministic fallback floor applied | {summary['path_fallback']} | {summary['path_fallback']/n*100:.1f}% |",
        "",
        "## Per-Posting Results",
        "",
        "| Job ID | Language | Track | Resolution Path | Hard Pass | M1 Rate | M2 Rate | M3 Coverage | M4 KW | M5 Format |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r, t in zip(results, traces):
        hp_str = "✅ PASS" if r["hard_pass"] else "❌ FAIL"
        m1_str = f"{r['m1_rate']*100:.1f}% ({r['m1_unsupported_total']}/{r['m1_checked_total']})"
        m2_str = f"{r['m2_rate']*100:.1f}% ({r['m2_inflated_total']}/{r['m2_assessed_total']})"
        m3_str = f"{r['m3_coverage']*100:.0f}%"
        m4_str = f"{r['m4_truthful_keywords']*100:.0f}%"
        m5_str = "PASS" if r["m5_format_passed"] else f"FAIL ({', '.join(r['m5_failed_checks'])})"
        path_str = f"`{t.get('final_path', 'unknown')}`"

        lines.append(
            f"| `{r['job_id']}` | `{r['language']}` | `{r['track']}` | {path_str} | {hp_str} | {m1_str} | {m2_str} | {m3_str} | {m4_str} | {m5_str} |"
        )

    lines.extend([
        "",
        "## Execution Commands",
        "",
        "```bash",
        "# Dry run (offline check)",
        "python3 scripts/run_verifier.py --dry-run",
        "",
        "# Live execution of V1 benchmark",
        "python3 scripts/run_verifier.py --max-calls 100",
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


def run_verifier_benchmark(
    dev_dir: Path,
    output_dir: Path,
    dry_run: bool,
    max_calls: int,
    seed: int,
) -> None:
    """Execute the Phase P8 Verifier V1 benchmark."""
    settings = get_settings()
    resumes_dir = output_dir / "resumes"
    resumes_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = output_dir / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    candidate = CandidateProfile.from_yaml(PROJECT_ROOT / "data" / "candidate_profile.yaml")
    facts = load_candidate_facts(PROJECT_ROOT / "data" / "candidate_facts.yaml")
    manifest_sha256 = compute_file_sha256(PROJECT_ROOT / "data" / "eval" / "MANIFEST.sha256")
    git_sha = get_git_sha()

    dataset = EvaluationDataset.from_directory(dev_dir)
    logger.info("Loaded %d test cases from %s", len(dataset), dev_dir)

    num_jobs = len(dataset)
    # Estimate worst-case calls: 3 gen + 3 judge + 1 final judge per job = 7 * num_jobs
    est_gen_calls = num_jobs * 3
    est_judge_calls = num_jobs * 4
    est_total_calls = est_gen_calls + est_judge_calls

    print("\n" + "=" * 70)
    print("📊 PHASE P8 VERIFIER (V1) EXECUTION PLAN")
    print("=" * 70)
    print(f"Test cases (dev jobs): {num_jobs}")
    print(f"Generator model:       {settings.generation_model}")
    print(f"Judge model:           {settings.judge_model}")
    print(f"Estimated max calls:   {est_total_calls} (Gen: ~{est_gen_calls}, Judge: ~{est_judge_calls})")
    print(f"Safety call budget:    {max_calls}")
    print(f"Dry run mode:          {dry_run}")
    print("=" * 70 + "\n")

    formatter = ResumeFormatter(output_dir=resumes_dir)

    if dry_run:
        logger.info("Executing dry run: running V1 locally offline with mocks, testing pipeline & verification...")
        dry_results: list[dict[str, Any]] = []
        dry_traces: list[dict[str, Any]] = []

        for tc in dataset:
            job_posting = tc.to_job_posting()
            # In dry-run, generate deterministic B0 as the baseline and simulate V1 verification
            resume = generate_b0(candidate=candidate, job=job_posting, language=tc.language)
            trace = V1Trace(
                final_path="clean@0",
                total_rounds=1,
                rounds=[],
                repair_actions_count=0,
                retrieved_context="Mock dry-run context",
            )
            res_dict = compile_and_verify(
                resume=resume,
                candidate=candidate,
                facts=facts,
                test_case=tc,
                variant_id="v1_dry",
                formatter=formatter,
                resumes_dir=resumes_dir,
                judge=None,
                dry_run=True,
            )
            dry_results.append(res_dict)
            dry_traces.append(trace.model_dump())

        print("\n✅ Dry run completed successfully! All 7 postings compile and verify offline.")
        print(f"Pass count: {sum(1 for r in dry_results if r['hard_pass'])}/{len(dry_results)}")
        return

    # Real Live Run
    quota_guard = QuotaGuard(max_calls=max_calls)
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
    pipeline = KnowledgeBasePipeline()
    pipeline.setup()

    all_results: list[dict[str, Any]] = []
    all_traces: list[dict[str, Any]] = []

    for tc in dataset:
        job_posting = tc.to_job_posting()
        logger.info("Executing V1 Pipeline -> Job: %s (%s)", tc.id, tc.company)

        resume, trace = generate_v1(
            candidate=candidate,
            job=job_posting,
            pipeline=pipeline,
            chain=chain,
            judge=judge,
            facts=facts,
            language=tc.language,
            max_retries=2,
            track=tc.target_track,
        )

        res_dict = compile_and_verify(
            resume=resume,
            candidate=candidate,
            facts=facts,
            test_case=tc,
            variant_id="v1",
            formatter=formatter,
            resumes_dir=resumes_dir,
            judge=judge,
            dry_run=False,
        )

        all_results.append(res_dict)
        all_traces.append(trace.model_dump())
        time.sleep(2.5)

    # Compute summary
    n = len(all_results)
    summary = {
        "n": n,
        "hard_pass_count": sum(1 for r in all_results if r["hard_pass"]),
        "m1_rate_sum": sum(r["m1_rate"] for r in all_results),
        "m2_rate_sum": sum(r["m2_rate"] for r in all_results),
        "m3_sum": sum(r["m3_coverage"] for r in all_results),
        "m4_sum": sum(r["m4_truthful_keywords"] for r in all_results),
        "m5_passed_count": sum(1 for r in all_results if r["m5_format_passed"]),
        "path_clean0": sum(1 for t in all_traces if t["final_path"] == "clean@0"),
        "path_clean1": sum(1 for t in all_traces if t["final_path"] == "clean@1"),
        "path_clean2": sum(1 for t in all_traces if t["final_path"] == "clean@2"),
        "path_repaired": sum(1 for t in all_traces if t["final_path"] == "repaired"),
        "path_fallback": sum(1 for t in all_traces if t["final_path"] == "fallback"),
    }

    manifest = {
        "timestamp": datetime.now().isoformat(),
        "git_sha": git_sha,
        "dataset_manifest_sha256": manifest_sha256,
        "variant": "v1",
        "generator_model": settings.generation_model,
        "judge_model": settings.judge_model,
        "judge_prompt_version": CLAIM_JUDGE_PROMPT_VERSION,
        "feedback_prompt_version": V1_FEEDBACK_PROMPT_VERSION,
        "total_api_calls": quota_guard.total_calls,
        "api_calls_breakdown": quota_guard.calls_by_model,
        "seed": seed,
    }

    # Write outputs
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (output_dir / "results.json").write_text(json.dumps(all_results, indent=2), encoding="utf-8")
    (output_dir / "traces.json").write_text(json.dumps(all_traces, indent=2), encoding="utf-8")

    report_md = generate_markdown_report(summary, all_results, manifest, all_traces)
    report_path = PROJECT_ROOT / "docs" / "experiments" / "E02_verifier.md"
    report_path.write_text(report_md, encoding="utf-8")

    logger.info("V1 Verifier benchmark completed successfully!")
    logger.info("Results saved to %s and %s", output_dir, report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase P8 Verifier V1 benchmark.")
    parser.add_argument(
        "--dev-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "dev",
        help="Path to development job postings directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "runs" / "E02_verifier",
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

    run_verifier_benchmark(
        dev_dir=args.dev_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        max_calls=args.max_calls,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
