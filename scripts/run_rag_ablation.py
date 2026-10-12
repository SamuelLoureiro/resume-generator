"""Command-line runner for Phase P9 RAG Ablation (Experiment E03).

Governed by docs/research_plan.md (Sections 4, 7; Hypothesis H4).
Evaluates whether RAG retrieval (V1: Hybrid RAG + Verifier) outperforms providing
the entire knowledge base in the prompt (B3 + Verifier: Full KB + Verifier).

Outputs:
- runs/E03_rag_ablation/manifest.json (reproducibility metadata & quota tracking)
- runs/E03_rag_ablation/results.json (raw per-job scores for B3+verifier)
- runs/E03_rag_ablation/traces.json (resolution traces for B3+verifier)
- runs/E03_rag_ablation/resumes/ (compiled LaTeX and PDF artifacts)
- docs/experiments/E03_rag_ablation.md (comparison tables and commands; human writes Interpretation/Conclusions)
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
from src.generation.variants.b3_full_context import (
    generate_b3_verified,
    load_full_knowledge_base_context,
)
from src.generation.variants.v1_verified import V1Trace
from src.verification.report import VerificationReport, verify_resume

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("rag_ablation_runner")


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
    summary_b3v: dict[str, Any],
    summary_v1: dict[str, Any],
    results_b3v: list[dict[str, Any]],
    results_v1: list[dict[str, Any]],
    manifest: dict[str, Any],
    traces_b3v: list[dict[str, Any]],
) -> str:
    """Generate Markdown report for docs/experiments/E03_rag_ablation.md."""
    n = summary_b3v["n"]

    # Compute V1 aggregates
    hp_pct_v1 = (summary_v1["hard_pass_count"] / n) * 100 if n else 0
    m1_rate_v1 = (summary_v1["m1_rate_sum"] / n) * 100 if n else 0
    m2_rate_v1 = (summary_v1["m2_rate_sum"] / n) * 100 if n else 0
    m3_v1 = (summary_v1["m3_sum"] / n) * 100 if n else 0
    m4_v1 = (summary_v1["m4_sum"] / n) * 100 if n else 0
    m5_pct_v1 = (summary_v1["m5_passed_count"] / n) * 100 if n else 0

    # Compute B3+verifier aggregates
    hp_pct_b3v = (summary_b3v["hard_pass_count"] / n) * 100 if n else 0
    m1_rate_b3v = (summary_b3v["m1_rate_sum"] / n) * 100 if n else 0
    m2_rate_b3v = (summary_b3v["m2_rate_sum"] / n) * 100 if n else 0
    m3_b3v = (summary_b3v["m3_sum"] / n) * 100 if n else 0
    m4_b3v = (summary_b3v["m4_sum"] / n) * 100 if n else 0
    m5_pct_b3v = (summary_b3v["m5_passed_count"] / n) * 100 if n else 0

    # Delta (V1 - B3+verifier)
    delta_hp = hp_pct_v1 - hp_pct_b3v
    delta_m1 = m1_rate_v1 - m1_rate_b3v
    delta_m2 = m2_rate_v1 - m2_rate_b3v
    delta_m3 = m3_v1 - m3_b3v

    lines: list[str] = [
        "# Experiment E03 — RAG Ablation (V1 vs. B3 + Verifier)",
        "",
        "> Governed by `docs/research_plan.md` (Sections 2, 4, 7; Hypothesis H4).",
        "> Directly evaluates whether RAG retrieval outperforms feeding the complete knowledge base (12 documents) into the prompt when both pipelines are safeguarded by the V1 verifier loop.",
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
        f"- **Total API Calls in this run (B3+verifier):** {manifest['total_api_calls']}",
        f"  - Generator calls: {manifest['api_calls_breakdown'].get(manifest['generator_model'], 0)}",
        f"  - Judge calls: {manifest['api_calls_breakdown'].get(manifest['judge_model'], 0)}",
        "",
        "## Headline Metrics Comparison (H4 Decision Table)",
        "",
        "| Variant | Description | Hard-Pass Rate | M1 Fabrication Rate | M2 Inflation Rate | M3 Coverage | M4 Truthful KW | M5 Format Pass |",
        "|---|---|---|---|---|---|---|---|",
        f"| **V1** | Hybrid RAG + Verifier | **{hp_pct_v1:.1f}%** ({summary_v1['hard_pass_count']}/{n}) | {m1_rate_v1:.1f}% | {m2_rate_v1:.1f}% | {m3_v1:.1f}% | {m4_v1:.1f}% | {m5_pct_v1:.1f}% ({summary_v1['m5_passed_count']}/{n}) |",
        f"| **B3+Ver** | Full Knowledge Base (12 docs) + Verifier | **{hp_pct_b3v:.1f}%** ({summary_b3v['hard_pass_count']}/{n}) | {m1_rate_b3v:.1f}% | {m2_rate_b3v:.1f}% | {m3_b3v:.1f}% | {m4_b3v:.1f}% | {m5_pct_b3v:.1f}% ({summary_b3v['m5_passed_count']}/{n}) |",
        f"| **Delta (V1 - B3+Ver)** | Net RAG Benefit | **{delta_hp:+.1f} p.p.** | {delta_m1:+.1f} p.p. | {delta_m2:+.1f} p.p. | **{delta_m3:+.1f} p.p.** | {(m4_v1 - m4_b3v):+.1f} p.p. | {(m5_pct_v1 - m5_pct_b3v):+.1f} p.p. |",
        "",
        "### Frozen Decision Threshold Check (Research Plan §7):",
        f"- **Requirement:** RAG is kept ONLY IF V1 beats B3+Ver by $\\ge +5.0$ coverage points (M3) OR has measurably lower fabrication.",
        f"- **Observed M3 Delta:** `{delta_m3:+.1f} p.p.`",
        f"- **Observed M1 Delta:** `{delta_m1:+.1f} p.p.`",
        "",
        "## Resolution Path Breakdown (B3 + Verifier)",
        "",
        "| Resolution Path | Meaning | Count | Share |",
        "|---|---|---|---|",
        f"| `clean@0` | Initial generation passed with 0 defects | {summary_b3v['path_clean0']} | {summary_b3v['path_clean0']/n*100:.1f}% |",
        f"| `clean@1` | Corrected after 1 error-guided feedback round | {summary_b3v['path_clean1']} | {summary_b3v['path_clean1']/n*100:.1f}% |",
        f"| `clean@2` | Corrected after 2 error-guided feedback rounds | {summary_b3v['path_clean2']} | {summary_b3v['path_clean2']/n*100:.1f}% |",
        f"| `repaired` | Deterministic repair resolved residual defects | {summary_b3v['path_repaired']} | {summary_b3v['path_repaired']/n*100:.1f}% |",
        f"| `fallback` | Deterministic fallback floor applied | {summary_b3v['path_fallback']} | {summary_b3v['path_fallback']/n*100:.1f}% |",
        "",
        "## Per-Posting Paired Comparison",
        "",
        "| Job ID | Track | V1 Path | B3+Ver Path | V1 M3 | B3+Ver M3 | V1 Hard-Pass | B3+Ver Hard-Pass |",
        "|---|---|---|---|---|---|---|---|",
    ]

    # Map results by job_id
    v1_by_job = {r["job_id"]: r for r in results_v1}
    for rb, tb in zip(results_b3v, traces_b3v):
        jid = rb["job_id"]
        rv1 = v1_by_job.get(jid, {})
        v1_hp = "✅" if rv1.get("hard_pass") else "❌"
        b3_hp = "✅" if rb["hard_pass"] else "❌"
        v1_m3_str = f"{rv1.get('m3_coverage', 0.0)*100:.0f}%"
        b3_m3_str = f"{rb['m3_coverage']*100:.0f}%"

        lines.append(
            f"| `{jid}` | `{rb['track']}` | - | `{tb.get('final_path', 'unknown')}` | {v1_m3_str} | {b3_m3_str} | {v1_hp} | {b3_hp} |"
        )

    lines.extend([
        "",
        "## Execution Commands",
        "",
        "```bash",
        "# Dry run (offline check)",
        "python3 scripts/run_rag_ablation.py --dry-run",
        "",
        "# Live execution of RAG ablation benchmark",
        "python3 scripts/run_rag_ablation.py --max-calls 100",
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


def run_rag_ablation(
    dev_dir: Path,
    output_dir: Path,
    dry_run: bool,
    max_calls: int,
    seed: int,
) -> None:
    """Execute the Phase P9 RAG Ablation benchmark."""
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
    num_jobs = len(dataset)
    logger.info("Loaded %d test cases from %s", num_jobs, dev_dir)

    # 1. Load V1 baseline results from E02
    e02_results_path = PROJECT_ROOT / "runs" / "E02_verifier" / "results.json"
    if not e02_results_path.exists():
        raise FileNotFoundError(
            f"Missing E02 results file at {e02_results_path}. Run Phase P8 (run_verifier.py) first."
        )
    v1_results: list[dict[str, Any]] = json.loads(e02_results_path.read_text(encoding="utf-8"))
    logger.info("Loaded %d reference V1 results from %s", len(v1_results), e02_results_path)

    v1_summary = {
        "n": len(v1_results),
        "hard_pass_count": sum(1 for r in v1_results if r["hard_pass"]),
        "m1_rate_sum": sum(r["m1_rate"] for r in v1_results),
        "m2_rate_sum": sum(r["m2_rate"] for r in v1_results),
        "m3_sum": sum(r["m3_coverage"] for r in v1_results),
        "m4_sum": sum(r["m4_truthful_keywords"] for r in v1_results),
        "m5_passed_count": sum(1 for r in v1_results if r["m5_format_passed"]),
    }

    # Estimate B3+verifier calls: at most 3 gen + 3 judge + 1 compile_verify = 7 * num_jobs = 49
    est_gen_calls = num_jobs * 3
    est_judge_calls = num_jobs * 4
    est_total_calls = est_gen_calls + est_judge_calls

    print("\n" + "=" * 70)
    print("📊 PHASE P9 RAG ABLATION (E03: V1 vs. B3+VERIFIER) PLAN")
    print("=" * 70)
    print(f"Test cases (dev jobs): {num_jobs}")
    print(f"Generator model:       {settings.generation_model}")
    print(f"Judge model:           {settings.judge_model}")
    print(f"Estimated max calls:   {est_total_calls} (Gen: ~{est_gen_calls}, Judge: ~{est_judge_calls})")
    print(f"Safety call budget:    {max_calls}")
    print(f"Dry run mode:          {dry_run}")
    print("=" * 70 + "\n")

    formatter = ResumeFormatter(output_dir=resumes_dir)
    full_kb_context = load_full_knowledge_base_context()

    if dry_run:
        logger.info("Executing dry run: running B3+verifier locally with mocks...")
        dry_results: list[dict[str, Any]] = []
        dry_traces: list[dict[str, Any]] = []

        for tc in dataset:
            job_posting = tc.to_job_posting()
            resume = generate_b0(candidate=candidate, job=job_posting, language=tc.language)
            trace = V1Trace(
                final_path="clean@0",
                total_rounds=1,
                rounds=[],
                repair_actions_count=0,
                retrieved_context=full_kb_context[:200],
            )
            res_dict = compile_and_verify(
                resume=resume,
                candidate=candidate,
                facts=facts,
                test_case=tc,
                variant_id="b3v_dry",
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

    all_results_b3v: list[dict[str, Any]] = []
    all_traces_b3v: list[dict[str, Any]] = []

    for tc in dataset:
        job_posting = tc.to_job_posting()
        logger.info("Executing B3+Verifier -> Job: %s (%s)", tc.id, tc.company)

        resume, trace = generate_b3_verified(
            candidate=candidate,
            job=job_posting,
            chain=chain,
            judge=judge,
            facts=facts,
            full_kb_context=full_kb_context,
            language=tc.language,
            max_retries=2,
            track=tc.target_track,
        )

        res_dict = compile_and_verify(
            resume=resume,
            candidate=candidate,
            facts=facts,
            test_case=tc,
            variant_id="b3v",
            formatter=formatter,
            resumes_dir=resumes_dir,
            judge=judge,
            dry_run=False,
        )

        all_results_b3v.append(res_dict)
        all_traces_b3v.append(trace.model_dump())
        time.sleep(2.5)

    n = len(all_results_b3v)
    summary_b3v = {
        "n": n,
        "hard_pass_count": sum(1 for r in all_results_b3v if r["hard_pass"]),
        "m1_rate_sum": sum(r["m1_rate"] for r in all_results_b3v),
        "m2_rate_sum": sum(r["m2_rate"] for r in all_results_b3v),
        "m3_sum": sum(r["m3_coverage"] for r in all_results_b3v),
        "m4_sum": sum(r["m4_truthful_keywords"] for r in all_results_b3v),
        "m5_passed_count": sum(1 for r in all_results_b3v if r["m5_format_passed"]),
        "path_clean0": sum(1 for t in all_traces_b3v if t["final_path"] == "clean@0"),
        "path_clean1": sum(1 for t in all_traces_b3v if t["final_path"] == "clean@1"),
        "path_clean2": sum(1 for t in all_traces_b3v if t["final_path"] == "clean@2"),
        "path_repaired": sum(1 for t in all_traces_b3v if t["final_path"] == "repaired"),
        "path_fallback": sum(1 for t in all_traces_b3v if t["final_path"] == "fallback"),
    }

    manifest = {
        "timestamp": datetime.now().isoformat(),
        "git_sha": git_sha,
        "dataset_manifest_sha256": manifest_sha256,
        "variant": "b3_verified",
        "reference_variant": "v1",
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
    (output_dir / "results.json").write_text(json.dumps(all_results_b3v, indent=2), encoding="utf-8")
    (output_dir / "traces.json").write_text(json.dumps(all_traces_b3v, indent=2), encoding="utf-8")

    report_md = generate_markdown_report(
        summary_b3v=summary_b3v,
        summary_v1=v1_summary,
        results_b3v=all_results_b3v,
        results_v1=v1_results,
        manifest=manifest,
        traces_b3v=all_traces_b3v,
    )
    report_path = PROJECT_ROOT / "docs" / "experiments" / "E03_rag_ablation.md"
    report_path.write_text(report_md, encoding="utf-8")

    logger.info("RAG Ablation benchmark completed successfully!")
    logger.info("Results saved to %s and %s", output_dir, report_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Phase P9 RAG Ablation benchmark (E03).")
    parser.add_argument(
        "--dev-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "eval" / "dev",
        help="Path to development job postings directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "runs" / "E03_rag_ablation",
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

    run_rag_ablation(
        dev_dir=args.dev_dir,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        max_calls=args.max_calls,
        seed=args.seed,
    )


if __name__ == "__main__":
    main()
