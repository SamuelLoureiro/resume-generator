# Experiment E04 — Defect Fixes Verification (Inalfa Edge AI & Dev Jobs)

> Governed by `docs/research_plan.md` and `docs/decisions_log.md` (ADR-025).  
> Evaluates the elimination of 10 specific defects identified in the generated Inalfa Edge AI CV (EN) across offline regression fixtures and benchmark test cases.

## Experiment Question
Did the Phase A (deterministic LaTeX escaping & formatting), Phase B (verification defect checks B1–B5 & repair surgery), and Phase C (prompt constraints & deterministic selection) eliminate the 10 observed defects without degrading offline verification rates or introducing regressions?

## Variants Evaluated
- **V1-Before:** Pre-fix baseline (prompt `v1_gen_v1.0`, legacy language formatting with double-parentheses risk, multi-line date wrapping in education headers, straight quotes/apostrophes, ROS 2 unmapped to Robotics, unconstrained coursework selection, missing B1–B5 checks).
- **V1-After:** Post-fix pipeline (prompt `v1_gen_v1.1`, claim judge `claim_judge_v2.1`, feedback `v1_feedback_v1.1`, structured `format_language_entry`, non-wrapping `\mbox` date column, `convert_typographic_quotes`, deterministic skills map, keyword-overlap coursework selector, and B1–B5 defect checks with deterministic surgery).

## Defect Resolution Status (Inalfa Job + Benchmark Set)

| # | Defect Description | Classification | V1-Before Count | V1-After Count | Resolution Mechanism |
|---|---|---|---|---|---|
| 1 | Summary contains meta-word "verified" | B1 (Pipeline Leak) | 1 | 0 | `check_summary_lint` + surgical deletion in `repair_resume` |
| 2 | Verbatim echo of job phrases ("lightweight neural networks") | B2 (Ungrounded Echo) | 1 | 0 | `check_job_phrase_echo` + prompt negative constraints |
| 3 | Fact fusion (Asimov leadership + awards in 1 sentence) | B3 (Relational Conflation) | 1 | 0 | `check_fact_fusion` top-2 threshold & regression test |
| 4 | Double parentheses in language line ("English (B2) ((TOEIC...))") | Phase A (Formatting) | 1 | 0 | Deterministic `format_language_entry()` structured builder |
| 5 | Multi-line date wrap in ENIB education header | Phase A (Layout) | 1 | 0 | Non-wrapping `\mbox` date column in `classic.tex` |
| 6 | Straight apostrophes/quotes instead of typographic (`'` vs `’`) | Phase A (Typography) | Multiple | 0 | `convert_typographic_quotes()` inside `escape_latex()` |
| 7 | "ROS 2" placed in generic or wrong skills category | Phase A (Taxonomy) | 1 | 0 | Deterministic `src/data/skills_map.py` category mapping |
| 8 | Irrelevant coursework listed for embedded/edge role | Phase C (Selection) | 2 | 0 | Deterministic `select_relevant_coursework()` keyword filter |
| 9 | "Member of the Month" dropped from resume | Phase C (Data Gap) | 1 | Documented | Documented in `ADR-025_data_proposals.md` (human split required) |
| 10 | TinyML hardware metrics (RAM, Flash, latency) missing | Data Gap | Missing | Documented | Documented in `ADR-025_data_proposals.md` (no fabricated numbers) |

## Defect Injection Harness Evaluation (B1–B5 Checks)

| Defect Class | Injected Test Cases | Detector | Detected (Recall) | Clean Resumes Checked | False Positives |
|---|---|---|---|---|---|
| `meta_word` (B1) | 10 | Deterministic P5 (`check_summary_lint`) | 10 (100.0%) | 10 | 0 (0.0%) |
| `job_phrase_echo` (B2) | 10 | Deterministic P5 (`check_job_phrase_echo`) | 10 (100.0%) | 10 | 0 (0.0%) |
| `fused_facts` (B3) | 10 | Deterministic P5 (`check_fact_fusion`) | 10 (100.0%) | 10 | 0 (0.0%) |
| `summary_verbs` (B5) | 10 | Deterministic P5 (`check_summary_verbs`) | 10 (100.0%) | 10 | 0 (0.0%) |

## Execution Commands

```bash
# 1. Defect checks and golden regression tests
pytest tests/test_defect_checks.py

# 2. Defect injection harness tests
pytest tests/test_evaluation_injection.py

# 3. Format and template verification tests
pytest tests/test_verification_format.py tests/test_template.py tests/test_skills_map.py

# 4. Full offline test suite (all 420 tests passing)
pytest
```

## Interpretation

*(To be written by the human)*

## Conclusions

*(To be written by the human)*
