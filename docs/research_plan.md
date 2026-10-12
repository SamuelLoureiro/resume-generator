# Research Plan — Grounded Resume Generation (v2, simplified)

> Destination in repo: `docs/research_plan.md`.
> **v2 (2026-10-01):** Scope reduced from 11 phases / 7 hypotheses to 9 phases / 4 hypotheses. Rationale: the project's primary goals are (1) learning RAG and LLMs deeply, and (2) building a portfolio piece that demonstrates that learning with honest results. A full academic protocol (bootstrap CI, held-out split, blind rating) exceeds what is needed and risks never finishing. The methodology stays rigorous where it matters (judge validation, deterministic checks, manifests) and is simplified where the overhead doesn't pay off (number of runs, statistical apparatus, two-step generation).
> Decision thresholds in section 7 are **proposals**. Adjust them **before** running any experiment, then freeze them (commit + ADR). Changing thresholds after seeing results invalidates the study.

## 1. Goals

1. **Product goal:** a generator that produces one-page resumes that are (a) faithful to the candidate profile, (b) complete with respect to what matters for the target job, and (c) readable by a recruiter.
2. **Learning goal:** understand which components (verification, RAG retrieval, prompt design, generator model) actually improve those properties, with evidence and honest negative results.

The product goal does not depend on the outcome of the study: verification (H1) is useful with or without RAG.

## 2. Hypotheses

| ID | Hypothesis |
|---|---|
| H0 | Baseline: measure the current pipeline (B1) and a deterministic no-LLM resume (B0). No claim, only a reference point. |
| H1 | A post-generation verifier with error-guided regeneration reduces fabrication and inflation to ~0 without reducing coverage. |
| H4 | RAG retrieval is **not** better than putting the whole knowledge base (12 docs) in the prompt. |
| H6 | A stronger generator model reduces inflation/fabrication independently of the prompt. |

**Dropped hypotheses and rationale:**
- ~~H2 (two-step generation):~~ Only worth testing if H1 (verifier) alone fails to solve hallucination. Revisit if V1 fabrication rate stays above 5%.
- ~~H3 (guidelines improve blind score):~~ Requires blind human rating as the primary signal, which is weak with n=1 rater. Guidelines are kept in the product regardless; we test their delivery mechanism (RAG vs full-context) via H4 instead.
- ~~H5 (hybrid > vector-only):~~ Interesting but lower priority than fixing fabrication. Can be added later as a quick ablation if time allows.
- ~~H7 (English KB for cross-lingual):~~ Interesting but out of scope for now.

Out of scope: any claim about ATS pass rates or interview outcomes. We cannot measure them.

## 3. Data

### 3.1 Job postings
- 5–8 **real** postings: mix of languages (EN, FR, PT), tracks (AI, data, backend, core SWE) and companies. The Amazon SDE Intern (Luxembourg) posting is one of them.
- All postings live in `data/eval/dev/`. No held-out split — with n < 10 jobs, a train/test split adds complexity without statistical power. This is acknowledged as a limitation (section 9).
- Record the SHA-256 of every job file in `data/eval/MANIFEST.sha256` so the dataset cannot silently change.
- Each job file: text plus a small header (`title`, `company`, `language`, `track`, `source_url`, `date_collected`). `track` is assigned by the human.

### 3.2 Profiles
- The real profile (`data/candidate_profile.yaml`, protected).
- 1–2 **synthetic** profiles, fully invented so the ground truth is known: (A) no professional experience, (B) research-only. They test that the system works beyond one person.

### 3.3 Atomic facts
`data/candidate_facts.yaml` — every claim the candidate is willing to make, one fact per line of evidence, with a **scope ceiling** (the strongest verb level that is truthful), tags, metrics and track relevance. Written and verified by the human. The agent never edits it.

### 3.4 Golden set (regression, not evaluation)
`tests/golden/` — the known defects of the Amazon resume turned into checks. It guarantees known errors do not return. It does **not** show the system is good; the benchmark does.

## 4. Variants

| ID | Description |
|---|---|
| B0 | Deterministic fallback (`build_fallback_tailored_resume`), no LLM. The floor. |
| B1 | Current pipeline: hybrid RAG, one-step generation. |
| B3 | Full knowledge base pasted into the prompt, no retrieval. |
| V1 | B1 + verifier with error-guided regeneration (max 2 retries, then deterministic repair). |

**Dropped variants and rationale:**
- ~~B2 (naive, no KB):~~ B0 already serves as the no-knowledge floor. B2 adds a run without adding insight.
- ~~B4 (vector-only):~~ Only needed for H5 (hybrid vs vector-only), which is deprioritized.
- ~~V2 (two-step + verifier):~~ Only needed for H2, which is deprioritized.
- ~~M-a/M-b (model ablation as separate variants):~~ Folded into H6 — run the best variant with both `gemini-3.5-flash-lite` and `gemini-3.8-flash` and compare.

Order: baselines (B0, B1, B3) → improvement (V1) → RAG ablation (V1 vs B3+verifier) → model effect. Fabrication is fixed **before** RAG is ablated, otherwise hallucination noise masks retrieval effects.

## 5. Metrics

Report each metric separately. **No aggregate/geometric mean** — it hides where the problem is. Headline: *hard-pass rate* = share of resumes with zero fabrication, zero inflation and all format checks passed.

| ID | Metric | How | Better |
|---|---|---|---|
| M1 | **Fabrication rate** = unsupported claims ÷ total claims | (a) skills/technologies must be in the profile allowlist (set check); (b) numbers must appear in the facts; (c) organizations, degrees, dates, titles must match the profile; (d) remaining free-text claims judged per-claim against the atomic facts by a *validated* judge (section 6) | lower |
| M2 | **Inflation rate** = bullets whose lead verb level > scope ceiling of the source fact | verb ladder below; bullet → fact mapping by nearest-fact matching with a threshold. Unmatched bullets are flagged into M1 | lower |
| M3 | **Coverage** = relevant facts present ÷ relevant facts | "relevant" = facts with `tracks` containing the job track and `priority ≤ 2`. Also list critical omissions | higher |
| M4 | **Truthful keyword alignment** = (job keywords ∩ resume ∩ profile allowlist) ÷ (job keywords ∩ profile allowlist) | Keywords the candidate does not really have are excluded from the denominator and counted as fabrication if present | higher |
| M5 | **Format constraints** | 1 page (`pdfinfo`), no empty section, section title matches content, contact in international format, URLs valid and not a bare profile page, single language, job title absent from the summary | all pass |

**M6 (blind human score) is dropped as a formal metric.** With n=1 rater who is also the author, it lacks validity as a deciding signal. Instead: after P7, read 3–5 generated PDFs end-to-end as a recruiter would. Write qualitative observations in `docs/lessons.md`. This is more honest and more useful for interviews than a pseudo-quantitative score.

### Verb ladder (scope levels)

| Level | Name | Example verbs (EN) — extend for FR/PT |
|---|---|---|
| 1 | participated | participated in, assisted, supported, took part in |
| 2 | contributed | contributed to, co-designed, co-developed, helped build |
| 3 | developed | developed, built, implemented, integrated, trained, wrote |
| 4 | led | led, managed, owned, founded, directed, coordinated, spearheaded |

Words such as *architected*, *engineered*, *designed* are treated as level 3 **only if** the fact ceiling is ≥ 3 and the fact really describes design; otherwise they count as inflation. The ladder file is proposed by the agent and **approved by the human**.

## 6. Validating the judge

An evaluator is only useful if it detects errors. Before trusting any LLM judge:

1. Take ≥ 10 clean resumes (hand-corrected Amazon resume, deterministic fallback resumes for several jobs, synthetic profiles).
2. Inject known lies with a seeded script, five types: fake skill, fake number, inflated verb, fake employer/degree, fabricated responsibility.
3. Run (i) the deterministic checks, (ii) the new claim-level judge, (iii) the **current** YES/NO faithfulness evaluator.
4. Report recall per lie type and false-positive rate on clean resumes.

Acceptance: recall ≥ 0.80 (deterministic checks ≥ 0.99 on the types they cover), false positives ≤ 0.10. A judge that fails is fixed or dropped. The number for the current evaluator is a result in itself (expected to be low: it scored 1.000 on resumes that contained unsupported claims).

Judge model ≠ generator model. Temperature 0. Judge prompt version is recorded in every run.

## 7. Protocol and decision rules

**Runs.** Each variant × job is run 1–2 times. With 1 run, report raw values per job. With 2 runs, report both and note any divergence. No statistical significance claims — the sample is too small and we acknowledge this.

**Manifest.** Every run writes `runs/<run_id>/manifest.json`: git SHA, variant, exact model IDs (never `-latest` aliases), temperature, max tokens, judge model and prompt version, dataset hash, seed, timestamp, number of API calls.

**One change per experiment.** Each experiment gets `docs/experiments/EXX_<name>.md` (question, variant, command, table, interpretation by the human) and, if a decision follows, an ADR.

**Decision rules (proposals):**

| Question | Supported / adopted if |
|---|---|
| H1 | mean M1 + M2 ≤ 5% **and** coverage drop ≤ 5 points vs B1 |
| H4 | RAG is kept **only if** it beats B3 by ≥ 5 coverage points or measurably lower fabrication; otherwise retrieval is retired to an optional module and documented honestly |
| H6 | report the difference; default model = best quality that fits the free quota |

## 8. Threats to validity

- **No held-out set:** all results are on the development set. Overfitting risk is real; mitigated by frozen thresholds and by not tuning prompts to specific jobs.
- **One real profile:** mitigated by 1–2 synthetic profiles.
- **LLM nondeterminism:** 1–2 runs per variant, pinned model IDs, manifests. Divergences between runs are reported, not averaged away.
- **Judge bias/leniency:** validation with injected lies (section 6); deterministic checks first.
- **Author = rater:** no formal blind rating. Qualitative impressions documented in `docs/lessons.md`, treated as anecdotal evidence, not a metric.
- **Small n (5–8 jobs):** no significance claims. Report raw numbers and patterns.
- **Free tier:** content may be used by the provider; contact data is not sent to the LLM (enforced after SEC-01 fix).

## 9. Phases and exit criteria

| Phase | Deliverable | Done when |
|---|---|---|
| 0 Audit | `docs/audit_report.md` | ✅ Human read it and confirmed findings in the code |
| 1 Model config | pinned IDs, judge ≠ generator | ✅ Config change + ADR-014; no `-latest` left |
| 2 Security & data fixes | Contact data stripped from prompts; phone/URL fixes | Contact not in LLM payload; tests enforce it |
| 3 Golden set | `tests/golden/` | Checks fail on the bad Amazon resume and pass on the corrected one |
| 4 Atomic facts | `data/candidate_facts.yaml` + `src/data/facts.py` | All facts verified by the human; every profile bullet maps to a fact |
| 5 Deterministic metrics | `src/verification/` | M1a–c, M2, M3, M4, M5 unit-tested on bad/good fixtures |
| 6 Judge validation | `docs/experiments/E00_judge.md` | Recall/FP reported for deterministic checks, new judge and old evaluator |
| 7 Baselines | `docs/experiments/E01_baselines.md` | B0, B1, B3 measured, 1–2 runs |
| 8 Verifier | `docs/experiments/E02_verifier.md` | H1 decision applied (B1 vs V1) |
| 9 RAG ablation | `docs/experiments/E03_rag_ablation.md` | H4 decision applied (V1 vs B3+verifier) |
| 10 Cleanup | docs, README, template fixes, `docs/lessons.md` | Docs match code; no unvalidated claims in README; lessons written |

**Dropped phases:**
- ~~P8 Two-step:~~ Only revisit if V1 fabrication stays above 5%.
- ~~P11 Held-out:~~ No held-out split with n < 10.

## 10. `docs/lessons.md`

One paragraph per phase/experiment on what surprised you. Include:
- What you expected vs. what happened
- The most interesting failure mode you found
- What you would do differently

This is the most valuable artifact for interviews. Write it as you go, not at the end.
