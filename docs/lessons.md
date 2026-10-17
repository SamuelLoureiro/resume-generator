# Engineering Lessons & Qualitative Reflections

> **Note on Authorship & Governance:** Governed by `.agents/GEMINI.md` and `docs/research_plan.md` (§10).
> This document synthesizes the qualitative engineering reflections, counter-intuitive findings, and architectural lessons gathered across the research, benchmarking, and refactoring phases (P0 through P10).

---

## 🧠 Core Conceptual Guide: What RAG Does, What It Did Here & Study Roadmap

### 1. What RAG (Retrieval-Augmented Generation) Actually Does (General Concept)
In traditional LLM generation, a model replies based exclusively on what was compressed into its static neural weights during pre-training. This creates two critical failure modes:
1. **Knowledge Cutoff & Stale Memory:** The model cannot know private, recent, or proprietary domain guidelines.
2. **Hallucination & Uncertainty:** When unsure or pressured by complex constraints, the model fabricates plausible-sounding but non-factual claims.

**RAG solves this by decoupling knowledge storage from language synthesis:**
- **Indexing:** External documents are chunked and stored in searchable indices (dense vector databases like ChromaDB and sparse lexical indices like BM25).
- **Retrieval:** When a query arrives, a retriever fetches only the most relevant passages.
- **Augmentation & Generation:** The retrieved passages are injected as explicit context into the LLM prompt, forcing the model to act as a grounded synthesizer rather than an ungrounded storyteller.

---

### 2. What RAG Specifically Did in This Project (The Big Architectural Difference)
A common misconception is assuming that RAG in this project was used to store and retrieve the candidate's personal resume data. **It was not.** The candidate's verified profile (`candidate_profile.yaml`) and atomic facts (`candidate_facts.yaml`) fit directly into the prompt.

**In this project, RAG was designed as an automated Expert Recruitment Consultant:**
- **The Knowledge Base:** We created a curated base of 13 Markdown guides covering ATS parsing standards, STAR/XYZ bullet formatting, and specialized recruiter expectations across 6 technical tracks (*AI/RAG, Data Science, Backend, Core SWE, Data Engineering, and Embedded Systems/Edge AI*).
- **The RAG Pipeline:** When you paste a job posting (e.g., Inalfa's automotive Edge AI internship), the hybrid retriever queries ChromaDB (`gemini-embedding-001`) and BM25, combining them via **Reciprocal Rank Fusion (RRF, $k=60$)**.
- **The Output:** The RAG engine dynamically selects the Top-5 most relevant recruitment guidelines (e.g., focusing on MCU memory footprints, C/C++ deterministic buses, and TinyML constraints) and injects only these ~1,200 words into the generation prompt.

---

### 3. Roadmap of Studies & What Each Experiment Proved

```mermaid
flowchart LR
    E00["E00: Judge Validation\n(Can we detect lies?)"] --> E01["E01: Baselines\n(Do LLMs lie without supervision?)"]
    E01 --> E02["E02: Verifier V1\n(Can we fix lies in closed-loop?)"]
    E02 --> E03["E03: RAG Ablation\n(Do we actually need RAG vs Long-Context?)"]
    E03 --> E04["E04: Real-World Inalfa\n(Does it survive a real job test?)"]
```

| Study | Core Question Asked | Key Finding & Breakthrough |
|---|---|---|
| **E00 (Judge Validation)** | *Can off-the-shelf evaluators reliably detect resume hallucinations?* | **No.** Off-the-shelf evaluators had 0% recall. We validated a new atomic claim-level judge (`claim_judge_v2.0` on `gemini-3.1-flash-lite`, temp 0.0) with **96.4% combined defect recall** and **0.92% false positive rate**. |
| **E01 (Baselines Benchmark)** | *How severe are hallucinations if an LLM generates a resume in one step?* | **Catastrophic.** Baseline B1 fabricated **11.71 claims/resume** and inflated 16.7% of verbs. B3 fabricated 7.43 claims. Both scored **0.0% Hard-Pass**. Single-step prompts cannot enforce truthfulness. |
| **E02 (Verifier V1)** | *Can an automated verifier loop with error-guided feedback eliminate hallucinations?* | **Yes.** Coupling multi-turn LLM regeneration with deterministic Python repair surgery reduced fabrication to **0.4%** and verb inflation to **0.0%**, while increasing factual coverage from 14.2% to **44.7%** (+30.5 p.p.). |
| **E03 (RAG Ablation)** | *In the era of 1M-token context windows, do we still need RAG, or can we just dump all 13 files into the prompt?* | **RAG won decisively.** RAG beat full context by **+7.2 percentage points in coverage** (44.7% vs 37.5%) with **4x fewer tokens**. Full-context stuffing caused "attention dilution", saturating the model with irrelevant track advice. |
| **E04 (Inalfa Real-World Test)** | *What unexpected edge cases occur when compiling a real resume for a niche job?* | Exposed subtle defects: passive cover-letter summaries, bus protocol conflation (SPI vs UART), and LaTeX template line wraps. Solved by adding Track 08 to the KB and hardening LaTeX formatting. |

---

## E00 — Judge Validation & Defect Injection Harness

- **What I expected vs. what happened:**
  - *Expectation:* I initially expected off-the-shelf evaluation frameworks (specifically LlamaIndex's `FaithfulnessEvaluator`) to detect obvious hallucinations, fabricated tools, and invented metrics.
  - *Reality:* The legacy evaluator scored **100% faithful (1.000)** on 28 corrupted resumes, exhibiting a **0.0% defect recall**. It suffered from severe holistic confirmation bias: because the candidate's genuine education and company names appeared in the context, the evaluator granted a blanket "YES" to the entire resume, ignoring fabricated metrics and tools.
  - *What worked:* Transitioning to atomic proposition extraction with an isolated judge (`gemini-3.1-flash-lite`, temperature 0.0, prompt version `claim_judge_v2.0`) achieved **90.0% recall on fabricated responsibilities (L5)** and **100.0% recall on cross-project conflations (L6)**, while keeping the claim-level false positive rate at **0.92%** (Wilson 95% CI: `[0.25%, 3.28%]`).

- **Most interesting failure mode found:**
  - *Relational Conflation (L6):* The LLM rarely fabricates completely alien technologies out of thin air. Instead, it steals legitimate tools from Project A (e.g., FreeRTOS or ROS 2) and splices them into Project B to artificially hit keywords from the job description. Holistic evaluators see the genuine tools in the profile context and approve the resume. Only atomic claim decomposition that explicitly binds `(entity, action, tool)` into a tuple can catch this behavior.
  - *Summary Blindness:* The legacy evaluator completely omitted the `objective_or_summary` field from evaluation, allowing the generator to claim unverified skills (like "distributed systems" or "scalable cloud software") with zero penalty.

- **What I would do differently:**
  - Never trust holistic binary evaluators from tutorial codebases for production grounding.
  - Build the synthetic defect injection harness (`src/evaluation/injection.py`) and golden fixtures on Day 1 before writing prompt templates.
  - Establish a strict division of labor early: use deterministic code/regex for entities, numbers, and dates (zero API cost, 100% precision) and reserve LLM judges strictly for semantic responsibility grounding.

---

## E01 — Baselines Benchmark (B0, B1, B3)

- **What I expected vs. what happened:**
  - *Expectation:* I expected that providing a strong negative prompt constraint (*"Never invent facts, use only verified candidate data"*) along with retrieved recruitment guidelines would produce reasonably faithful resumes.
  - *Reality:* Both unverified baselines suffered catastrophic hallucination rates. Baseline B1 (Hybrid RAG) fabricated an average of **11.71 unsupported claims per resume**, while B3 (Full Knowledge Base in Prompt) fabricated **7.43 claims per resume**. Both achieved **0.0% Hard-Pass** across all benchmark postings.
  - *The Verb Inflation Phenomenon:* Prompts instructing the model to use "strong, active verbs" (Google XYZ formula) triggered massive verb inflation (**16.7% in B1**, **28.6% in B3**), systematically upgrading junior team assistance or operational management into senior architectural leadership (*"Architected"*, *"Spearheaded"*).

- **Most interesting failure mode found:**
  - *The 1-Page Budget Squeeze:* When forced to fit a strict 1-page visual budget while simultaneously maximizing ATS keyword matches, the LLM silently dropped the candidate's most significant verified accomplishments—such as leading 5+ developers at Asimov Jr., winning "Area of the Month", and serving on the SPE student board—in order to make room for synthesized generic bullets loaded with target keywords. Single-step prompts sacrifice factual density for surface-level keyword alignment.

- **What I would do differently:**
  - Discard the myth that prompt engineering alone can eliminate hallucinations. A single LLM invocation cannot simultaneously optimize four competing objectives: typography/page constraints, ATS keyword density, persuasive impact, and strict factual truthfulness.
  - Treat truthfulness as an architectural invariant enforced by an external post-generation supervisor rather than an internal prompt instruction.

---

## E02 — Verifier V1 (Error-Guided Regeneration & Deterministic Surgery)

- **What I expected vs. what happened:**
  - *Expectation:* I expected the LLM to resolve all detected issues cleanly on the first regeneration attempt once given an error list.
  - *Reality:* `clean@0` was **0.0%**, confirming that zero-shot generation never produces a defect-free resume. Multi-turn feedback resolved issues in only 28.6% of cases (`clean@1` and `clean@2`). In the remaining cases, the LLM struggled with negative constraints (e.g., repeatedly trying to sneak back a keyword or rephrasing a forbidden tool).
  - *The Power of Deterministic Surgery:* The breakthrough was pairing LLM regeneration with deterministic repair surgery (`src/verification/repair.py`). When the LLM exhausted its retry budget, deterministic code stripped unverified skills, clamped verbs along the 4-level Verb Ladder, aligned corrupted dates with ground truth, and restored verified fallback bullets. This drove the fabrication rate down to **0.4%** and verb inflation to **0.0%**, while increasing requirement coverage by **+30.5 percentage points** over B1.

- **Most interesting failure mode found:**
  - *Micro-extrapolations caught by the Atomic Judge:* In the French Stellantis posting, the verified fact stated "routing and ground plane layouts in EasyEDA". The generator wrote "routage multicouche" (multilayer routing). Although technically plausible in electronics, the specific word "multicouche" was absent from the verified fact text. The atomic claim judge flagged it with surgical precision. This demonstrated that an isolated judge operating at temperature 0.0 with frozen facts catches subtle domain extrapolations that human reviewers routinely miss.

- **What I would do differently:**
  - Cap LLM regeneration at 2 retries (or even 1) before triggering deterministic surgery. Giving the model 3+ retries burns latency and token quota with diminishing returns; deterministic repair solves mechanical violations instantaneously at zero token cost.
  - Implement language-aware fallback generation so that B0 fallbacks translate bullets into the target posting language (resolving the M5 `single_language` failure on Portuguese/French postings).

---

## E03 — RAG Ablation (V1 vs. B3 + Verifier)

- **What I expected vs. what happened:**
  - *Expectation:* In the era of massive context windows (Gemini Flash handling 1M+ tokens), I hypothesized that dumping all 12 knowledge base documents (~5,400 words) directly into the prompt (B3 + Verifier) might render RAG obsolete.
  - *Reality:* Hybrid RAG (V1) decisively outperformed full-context stuffing by **+7.2 percentage points in requirement coverage** (44.7% vs. 37.5%), comfortably exceeding the research plan's frozen decision threshold of $\ge +5.0\text{ p.p.}$.
  - *Token Efficiency:* V1 used **~1,200 words** per prompt turn (Top-5 chunks) compared to **~5,400 words** for B3+Ver. Over a 3-turn verifier loop, B3 consumed >4x more prompt tokens while achieving worse coverage.

- **Most interesting failure mode found:**
  - *Attention Dilution & Guideline Saturation:* Feeding the entire knowledge base unconditionally cluttered the generation prompt with off-track guidelines (e.g., Data Engineering pipeline tips on an Embedded Systems job). The LLM's attention was diluted by irrelevant advice, leading it to over-prune relevant candidate bullets during regeneration. On the French Stellantis posting, B3+Ver over-pruned bullets down to 0% coverage, whereas V1 preserved 43% coverage.

- **What I would do differently:**
  - Always empirically test the "just stuff it in the prompt" hypothesis before declaring RAG necessary. RAG's true value here was not retrieving obscure trivia, but **noise reduction and attention focusing**: delivering only the track-specific guidance the generator needed to align the candidate's real experiences with the job.

---

## E04 & Real-World Post-P10 Validation (Inalfa Edge AI Case)

- **What I expected vs. what happened:**
  - *Expectation:* Once the benchmark passed, I expected real-world resume generation via Gradio to be defect-free.
  - *Reality:* Testing a real-world automotive ECU internship posting (Inalfa Roof Systems) revealed several subtle qualitative and typographic defects:
    1. *Passive summary phrasing:* The model fell back to generic cover-letter clichés (*"applying for the AI Processing in ECU internship ... to contribute to..."*) instead of presenting an active Technical Value Proposition.
    2. *Hardware protocol conflation:* The model merged SPI and UART into a single sentence (*"custom SPI and UART protocols"*), confusing inter-board master-slave communication with PC telemetry.
    3. *Template formatting flaws:* An education `\newline` left "France" isolated on its own line; date ranges used simple hyphens instead of LaTeX en-dashes (`--`); and empty certifications caused duplicate section headers (`\section{Languages}` followed by `\textbf{Languages:}`).
  - *The Solution:* Instead of patching prompts with ad-hoc rules, we expanded the Knowledge Base with a dedicated Embedded Systems track ([`08_embedded_systems_and_edge_ai.md`](file:///home/samuel/Documentos/Proj_pessoal/gerador_curriculos/src/knowledge_base/hr_recruitment/08_embedded_systems_and_edge_ai.md)), added Mandate 1 grounding directives to separate hardware buses, hardened the LaTeX template for inline locations and en-dashes, and verified the output with V1 (`clean@1`, Hard Pass = True, exactly 1 page).

- **Most interesting failure mode found:**
  - *The "Double Parenthesis" Typographic Trap:* The candidate profile had `proficiency: "Advanced (C1 - TOEIC)"`. When wrapped in template parentheses `(<< lang.proficiency >>)`, the output ended in `...TOEIC))` (two consecutive closing parentheses). Attempting to sanitize this string via Jinja2 regex mutated the underlying schema, breaking bidirectional round-trip tests (`ResumeSchema <-> LaTeX`). The lesson: keep template rendering strictly idempotent and fix data formatting at the source (`candidate_profile.yaml`).

- **What I would do differently:**
  - Maintain the candidate ground truth as an immutable contract. Never mutate candidate facts inside Jinja templates to solve visual quirks; address formatting structurally in the template engine and keep data clean.

---

## General Reflections on RAG, Grounding & LLMs in Production

1. **Prompts are Suggestions; Compilers & Parsers are Guarantees:**
   - Prompts cannot enforce zero hallucination. When an LLM faces conflicting objectives (e.g., "be truthful" vs. "include ATS keywords" vs. "fit 1 page"), it will inevitably compromise truthfulness. A production system must treat the LLM as an untrusted proposal engine, followed by a deterministic compiler, validator, and repair supervisor.

2. **The Verb Scope Ceiling (Verb Ladder):**
   - In technology resumes, verb inflation is the most insidious form of fabrication because it transforms real work into an untruthful claim of seniority. Organizing verbs into an audited 4-level ladder (*Level 1: participated $\rightarrow$ Level 2: contributed $\rightarrow$ Level 3: developed $\rightarrow$ Level 4: led*) and bounding each atomic fact with a maximum allowed level is essential for ethical, verifiable career representation.

3. **Privacy by Architecture (SEC-01):**
   - Personal Identifiable Information (email, phone, address, profile links) should never enter the LLM's context window. Stripping contact data before prompt construction and injecting it into the LaTeX template at compile time is a zero-latency, zero-cost privacy guarantee that eliminates data leakage risks.

4. **Hybrid Search is Non-Negotiable for Technical Domains:**
   - Dense semantic embeddings fail on exact hardware identifiers, microcontroller models, and specialized bus protocols (e.g., `RP2350`, `MPU9250`, `STM32`, `CAN Bus`, `FreeRTOS`). BM25 sparse keyword search handles exact acronyms, while dense embeddings capture conceptual relevance. Reciprocal Rank Fusion (RRF, $k=60$) is lightweight, parameter-free, and consistently outperforms single-modality retrievers.

5. **Fail-Closed Safety Floors:**
   - For high-stakes document generation (resumes, legal contracts, medical reports), a system must never fail open by emitting an unverified hallucination. Implementing a deterministic fallback floor (B0) ensures that even in the event of an API failure or unresolvable regeneration loop, the candidate is always represented by verified, grounded facts.
