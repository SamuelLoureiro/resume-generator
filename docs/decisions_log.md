# Technical Decisions Log (ADRs)

## ADR-001: Google Gemini as LLM Provider
- **Date:** 2026-09-22
- **Status:** Accepted
- **Context:** Need to choose an LLM provider for generation and embeddings.
- **Decision:** Google Gemini (models 2.5 Flash and Pro) via API.
- **Rationale:** User holds a Google AI Pro subscription at no extra cost. Competitive quality against GPT-4o.
- **Consequences:** Dependency on the Google ecosystem; good integration with LlamaIndex.

## ADR-002: LlamaIndex as RAG Framework
- **Date:** 2026-09-22
- **Status:** Accepted
- **Context:** Choice between LangChain and LlamaIndex for the RAG pipeline.
- **Decision:** LlamaIndex.
- **Rationale:** More focused and intuitive API for RAG; better abstractions for indexing and retrieval.
- **Consequences:** Less flexibility for complex chains, but sufficient for the use case.

## ADR-003: PDF Output via LaTeX
- **Date:** 2026-09-22
- **Status:** Accepted
- **Context:** Output format for the generated resume.
- **Decision:** PDF generated via LaTeX compilation (Jinja2 template → .tex → pdflatex → .pdf).
- **Rationale:** Superior typographic quality; precise layout control; academic/professional standard.
- **Consequences:** Requires a LaTeX distribution (texlive); higher complexity than DOCX.

## ADR-004: Gradio as Interface Framework
- **Date:** 2026-09-22
- **Status:** Accepted
- **Context:** UI framework for demonstration and usage of the system.
- **Decision:** Gradio instead of Streamlit.
- **Rationale:** Easy deployment on HuggingFace Spaces; simple API; well-suited for ML demos.
- **Consequences:** Less layout flexibility than Streamlit, but sufficient for the use case.

## ADR-005: ChromaDB as Vector Store
- **Date:** 2026-09-22
- **Status:** Accepted
- **Context:** Need to store and search embeddings.
- **Decision:** ChromaDB with local persistence.
- **Rationale:** Lightweight, no external infrastructure, good integration with LlamaIndex.
- **Consequences:** Does not scale to millions of documents, but the dataset is small.

## ADR-006: Codebase Standardization to English
- **Date:** 2026-09-25
- **Status:** Accepted
- **Context:** Initial code, docs, and comments were partially written in Portuguese, reducing readability for international contributors and tools.
- **Decision:** Migrate all identifiers, comments, docstrings, logs, documentation, and planning files to idiomatic English. Runtime data values (e.g. candidate profile content, knowledge base documents) remain in Portuguese where applicable.
- **Rationale:** Consistent English codebase improves maintainability, static analysis, and portfolio presentation.
- **Consequences:** One-time translation effort across all modules; no runtime logic changes.

## ADR-007: Hybrid Search with Reciprocal Rank Fusion (RRF)
- **Date:** 2026-09-25
- **Status:** Accepted
- **Context:** Internship job postings combine broad semantic domain intent (e.g. "AI engineering") with exact technical stack terms (e.g. "FastAPI", "PyTorch", "ChromaDB"). Pure vector search may miss exact keyword hits, while pure keyword search misses conceptual semantic relevance.
- **Decision:** Implement `HybridResumeRetriever` combining dense vector search (ChromaDB cosine similarity) and sparse keyword search (BM25 via `llama-index-retrievers-bm25`), fused with Reciprocal Rank Fusion (RRF, constant k=60).
- **Rationale:** RRF is parameter-free, avoids score scale mismatch between cosine similarity and BM25 scores, and ensures both semantic relevance and exact keyword presence are rewarded.
- **Consequences:** Requires building an in-memory BM25 index over candidate nodes; minimal memory footprint for small-to-medium knowledge bases.

## ADR-008: Structured Generation with Pydantic v2 & Anti-Hallucination Guardrails
- **Date:** 2026-09-25
- **Status:** Accepted
- **Context:** LLMs naturally tend to hallucinate credentials or rephrase experiences in ways that alter factual truth when tailoring resumes. Furthermore, unstructured markdown responses require fragile post-processing.
- **Decision:** Combine Google Gemini with a five-mandate system prompt enforcing factual grounding exclusively on `CandidateProfile`, and require structured JSON output parsed into `TailoredResume` (Pydantic v2). Provide resilient extraction (`extract_json_payload`) supporting raw JSON, markdown-wrapped JSON, and embedded objects.
- **Rationale:** Strict schema validation catches hallucinated attributes immediately, while the prompt design channels the LLM's creativity toward stylistic tailoring (Google XYZ formula, active verbs) rather than factual invention.
- **Consequences:** Generates valid, type-safe data structures ready for deterministic Jinja2/LaTeX rendering.

## ADR-009: LlamaIndex Native Evaluators Instead of RAGAS 0.4.x
- **Date:** 2026-09-25
- **Status:** Accepted
- **Context:** Phase 5 requires evaluation of three quality dimensions: faithfulness (anti-hallucination), answer relevancy, and context precision — the standard RAGAS metrics. RAGAS was declared as a project dependency since initial planning. When RAGAS 0.4.3 was installed, it failed to import because `ragas/llms/base.py` hardcodes `from langchain_community.chat_models.vertexai import ChatVertexAI`, a module that no longer exists in `langchain-community >= 0.3.x` (the VertexAI integration was moved to the separate `langchain-google-vertexai` package). Installing `langchain-google-vertexai` does not resolve the issue because the import uses the old `langchain_community` namespace, not the new package's namespace.
- **Decision:** Use `llama_index.core.evaluation` evaluators (`FaithfulnessEvaluator`, `RelevancyEvaluator`, `ContextRelevancyEvaluator`) instead of RAGAS directly.
- **Rationale:**
  - LlamaIndex evaluators measure the exact same three dimensions as RAGAS with identical 0-1 scoring convention.
  - They use our existing Gemini LLM configuration (`get_gemini_llm()`), requiring no additional LLM setup.
  - They are natively integrated with LlamaIndex's node and response structures, requiring no data format conversion layer.
  - All three evaluator APIs are identical: `evaluate(query, response, contexts)`, simplifying the runner implementation.
  - Unit tests run fully offline using `MagicMock` (no `MockLLM` required), since evaluator methods are patched directly.
- **Consequences:** RAGAS remains listed in `pyproject.toml` as an optional dependency for future compatibility (it can replace LlamaIndex evaluators if a compatible version is released). The evaluation report includes `| RAGAS Parallel |` columns mapping our metrics back to the RAGAS terminology for familiarity.

## ADR-010: Knowledge Base Domain Specialization & Retrieval Candidate Expansion
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Baseline evaluation in Task 5.2 exposed a significant drop in `Context Precision` for roles outside AI/RAG (notably Data Engineering at 0.375 and Core SWE at 0.625). Qualitative evaluator analysis confirmed that the knowledge base lacked dedicated guidelines for data pipelines, SQL modeling, C/C++, algorithms, and competitive programming, forcing the hybrid retriever to pull generic advice.
- **Decision:**
  1. Expand the knowledge base with dedicated documents: `06_data_engineering_internships.md` and `07_systems_and_core_swe_internships.md`, and update `05_adaptation_by_technical_track.md` to formally cover all 5 tracks.
  2. Increase candidate retrieval pools in `HybridResumeRetriever` and `KnowledgeBasePipeline` from 5 to 8 (`similarity_top_k=8`, `bm25_top_k=8`), providing richer inputs to Reciprocal Rank Fusion (RRF) before truncating to `top_k`.
  3. Introduce collection recreation support (`recreate: bool = False`) in `KnowledgeBaseIndexer` and `--reindex` CLI flag in `benchmark.py` to ensure clean vector database rebuilds.
- **Rationale:** High-signal, domain-specific chunks give the LLM concrete guidelines for adapting resumes to distinct technical expectations, while expanding the pre-fusion candidate window prevents specialized keyword matches from being pruned prematurely.
- **Consequences:** Average Context Precision increased from `0.725` to `0.900` (+17.5%), with Data Engineering and Core SWE jumping from 0.375/0.625 to a perfect `1.000`. Overall Aggregate score rose from `0.898` to `0.965`.

## ADR-011: Defensive Fallbacks and Adversarial Edge-Case Hardening
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Production RAG applications face edge cases such as adversarial prompt injections in job descriptions, minimal profiles with 0 previous jobs, sparse job descriptions without requirements or tech stacks, exotic LaTeX-breaking characters, and potential LLM API downtime or quota exhaustion.
- **Decision:**
  1. Implement `build_fallback_tailored_resume(candidate, job)`: a deterministic, zero-hallucination resume generator drawing directly from the verified candidate profile and formatting it into a valid `TailoredResume` structure.
  2. Add `allow_fallback: bool = False` to `ResumeGenerationChain.generate()` to gracefully handle malformed responses or API outages when operating in production/UI mode.
  3. Harden `JobPosting.to_search_query()` to sanitize empty/whitespace elements, preventing empty query strings.
  4. Harden `build_resume_generation_prompt()` to insert explicit fallback instructions when retrieved knowledge guidelines are empty.
  5. Harden `sanitize_filename_part()` with a configurable `fallback` default to prevent empty filename stems when company names consist exclusively of symbols.
  6. Create dedicated test suite `tests/test_edge_cases.py` (15 tests) verifying all adversarial, edge-case, and fallback pathways.
- **Rationale:** Guarantee 100% pipeline reliability and zero-crash operation without compromising the strict anti-hallucination mandate.
- **Consequences:** The system gracefully handles adversarial injections, minimal student profiles with 0 experiences, missing job requirements, and API errors, delivering a fully-formed, compilable LaTeX PDF under all tested edge cases.

## ADR-012: Containerization, Portfolio Packaging, and Deployment Readiness
- **Date:** 2026-09-27
- **Status:** Accepted
- **Context:** Delivering the project as a portfolio showcase and production-ready service requires reproducible execution across environments without requiring users to locally install Rust, Tectonic, or Python 3.12. Additionally, the web app should be deployable to platforms like Hugging Face Spaces or container clusters.
- **Decision:**
  1. Author a production-ready `Dockerfile` based on `python:3.12-slim`, downloading the precompiled standalone static Tectonic binary (v0.15.0). Total image remains under 400 MB.
  2. Implement non-root user execution (UID 1000) compliant with Hugging Face Spaces Docker container requirements.
  3. Provide `docker-compose.yml` with host volume mounts for persistent ChromaDB storage and generated PDF output directory.
  4. Create root entrypoint `app.py` for direct Hugging Face Spaces integration.
  5. Author an exhaustive, publication-grade `README.md` complete with badges, architecture flowcharts (Mermaid), benchmark comparison tables, quickstart guides, and ADR index.
- **Rationale:** Ensures frictionless one-command deployment (`docker compose up --build`), eliminates environmental discrepancies, and positions the codebase as a high-standard portfolio project.
- **Consequences:** The application is self-contained, reproducible, secure, and ready for immediate deployment on container runtimes and Hugging Face Spaces.

## ADR-013: Multilingual Support (PT / EN / FR) & Strict 1-Page Layout Budget
- **Date:** 2026-09-29
- **Status:** Accepted
- **Context:** Resumes generated for English job postings (such as an AI internship at Philips) exhibited two layout and stylistic issues: (1) section headers and template labels remained hardcoded in Portuguese while body text was in English; (2) the document spilled into a 2nd page by ~40-50pt because of loose margins (0.55in) and excessive section spacing. Additionally, the user requested full native support for French (`fr`), as European internship opportunities (e.g. in France) require strictly francophone documents.
- **Decision:**
  1. **Dynamic Multilingual Labels:** Introduce `ResumeLanguageCode = Literal["pt", "en", "fr"]` and `SECTION_LABELS` in `src/data/resume.py`. Dynamically inject escaped section titles and field labels (`objective`, `education`, `experience`, `projects`, `skills`, `languages_certs`, `technologies`, `view_project`, etc.) into `to_latex_context()`.
  2. **Heuristic Language Detection:** Implement `detect_language_from_text()` in `src/generation/chain.py` to auto-detect whether a job posting is in French, English, or Portuguese based on domain keywords and characteristic stopwords.
  3. **UI Language Selection:** Add a language dropdown in Gradio (`src/app.py`): `Automático (detectar da vaga)`, `Português (PT-BR)`, `Inglês (EN)`, `Francês (FR)`.
  4. **Strict 1-Page Layout & Spacing:** Refactor `templates/resume.tex.j2` geometry to `margin=0.46in, top=0.40in, bottom=0.40in`, tighten `titlesec` spacing to `5pt/2.5pt`, and tighten `enumitem` list item separation to `0.8pt/0.5pt`.
  5. **1-Page Budget & Language Mandate in Prompts:** Update `SYSTEM_PROMPT` and `build_resume_generation_prompt()` in `src/generation/prompts.py` to enforce a strict single-page content budget (maximum 2-3 bullets per role/project, max 1 concise line of coursework per degree) and strict target language consistency (100% of generated content in the selected language).
- **Rationale:** Ensures international versatility across Brazilian, Anglophone, and Francophone tech markets, while guaranteeing ATS-compliant single-page resumes.
- **Consequences:** Prevents page spillover across all candidate profiles and produces harmonious, professionally localized documents in French, English, or Portuguese.

## ADR-014: Pinned Models and Separate Evaluation Judge
- **Date:** 2026-10-01
- **Status:** Accepted
- **Context:**
  - Automated evaluation of the RAG resume generation pipeline requires assessing faithfulness, relevancy, and context precision without self-evaluation bias. Previously, floating aliases like `models/gemini-flash-lite-latest` and silent overrides in `src/generation/chain.py` caused both the generator and the evaluation judge to default to the same model or unpinned checkpoints.
  - Running automated benchmarks under Google AI Studio free tier introduces strict quota constraints:
    1. Pro models (`gemini-2.5-pro`, `gemini-3.1-pro`) are not available on the free tier.
    2. Full Flash models (`gemini-3.8-flash`, `gemini-2.5-flash`) have very low daily request limits (15-50 requests/day), which would instantly exhaust the quota during benchmark sweeps.
    3. Flash-Lite models (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`) provide generous throughput (~1,500 requests/day), enabling repeatable benchmark runs and regression sweeps without billing.
- **Decision:**
  1. **Explicit Pinned Settings:** Add explicit settings in `src/config.py` and `.env.example`:
     - `GENERATION_MODEL=gemini-3.5-flash-lite` (default, temperature 0.3) for resume generation and benchmark runs.
     - `JUDGE_MODEL=gemini-3.1-flash-lite` (default, temperature 0.0) for evaluation judge.
     - `gemini-3.8-flash` is designated and allowed as an override for real-world resume generation.
  2. **Remove Floating Aliases & Hardcoded Overrides:** Remove all `-latest` aliases and hardcoded model IDs outside `src/config.py`, including the silent model rewrite in `src/generation/chain.py`.
  3. **Strict Separation Validation:** Add startup validation in `Settings` (`@model_validator(mode="after")`) ensuring `GENERATION_MODEL` and `JUDGE_MODEL` are distinct (normalizing whitespace and `models/` prefix). If identical, raise a clear `ValueError` to prevent self-evaluation bias.
  4. **Single-Call Discovery Script:** Provide `scripts/list_models.py` to list models available to the key and verify that configured IDs exist in the API catalog.
  5. **Offline Unit Tests:** Add comprehensive unit tests in `tests/test_config.py` verifying defaults, distinctness validation, and temperature constraints.
- **Consequences:** Pipeline configuration is explicit and auditable; accidental identical generator/judge setups fail immediately; benchmark volume is sustainable on free tier.

## ADR-015: Render-Time Contact Injection, PII Privacy Protection, and Template Sanitization
- **Date:** 2026-10-01
- **Status:** Accepted
- **Context:**
  - Audit finding SEC-01 revealed that personal candidate contact data (`candidate.contact`: full name, email, phone, address, profile links) was being serialized to plain JSON and transmitted across the network to Google's external Gemini API on every generation run.
  - Finding TPL-01 showed that `templates/resume.tex.j2` statically rendered the header "Languages & Certifications" even when the certifications list was empty.
  - Findings DAT-01, DAT-02, DAT-03 showed phone number format errors in French notation (`+33 07...` instead of `+33 7...`), missing `https://` protocol schemes causing PDF viewers to treat profile links as relative local filesystem paths, and a project URL pointing to a general GitHub profile rather than a repository.
- **Decision:**
  1. **Strip Contact Info from Prompt (SEC-01):** In `src/generation/prompts.py`, remove `contact` from `candidate_data` before JSON serialization. Remove `header` from the requested JSON schema in prompt instructions, adding an explicit directive instructing the model not to output personal contact details.
  2. **Deterministic Contact Injection in Chain:** In `src/generation/chain.py`, provide fallback empty header handling in `parse_tailored_resume()`, and deterministically inject verified `ResumeHeader` from `candidate.contact` inside `ResumeGenerationChain.generate()`.
  3. **Render-Time Injection in Formatter:** In `src/generation/formatter.py`, accept an optional `contact: ContactInfo | None = None` parameter in `render_latex()` and `compile_pdf()` to ensure verified contact details can be injected directly into LaTeX template context. Pass `contact=candidate.contact` from `src/app.py`.
  4. **Automatic URL Protocol Scheme Sanitization:** In `src/data/resume.py`, add `@field_validator` on `ResumeHeader` and `ResumeProject` that prepends `https://` if a URL string does not start with `http://` or `https://`.
  5. **Dynamic Section Titles (TPL-01):** Add localized labels `languages_only` ("Idiomas", "Languages", "Langues") and `certifications_only` ("Certificações", "Certifications") to `SECTION_LABELS`. Update `templates/resume.tex.j2` to conditionally render the title matching the populated items.
  6. **Data Profile Corrections (DAT-01, DAT-02, DAT-03):** Correct phone number format to `+33 7 43 52 84 87`, add `https://` to LinkedIn and GitHub URLs, and reset TinyML project URL to `""` in `data/candidate_profile.yaml`.
  7. **Enforcement Tests:** Add unit tests `test_contact_info_not_leaked_in_prompt`, `test_chain_generates_resume_with_verified_contact`, `test_formatter_render_latex_with_contact_override` in `tests/test_generation.py`, and `test_template_languages_certifications_conditional_headers` in `tests/test_template.py`.
- **Rationale:** Strict compliance with project security rules (`GEMINI.md`) and GDPR/privacy best practices: personal contact data must never be transmitted to external LLMs when it can be injected deterministically into the presentation layer. Eliminates formatting bugs and broken links in generated PDFs.
- **Consequences:** Zero contact PII is sent to external LLMs. Contact headers and URLs in generated resumes are guaranteed to match candidate ground truth.

## ADR-016: Golden Set Regression Suite for Defect Anchoring
- **Date:** 2026-10-03
- **Status:** Accepted
- **Context:**
  - In Phase P3 of the research plan (`docs/research_plan.md`), the defects identified during the audit (`docs/audit_report.md`) on the Amazon SDE Intern resume must be converted into permanent regression checks.
  - Known failure modes included:
    1. Fabricated technical claims ("distributed systems", "scalable cross-platform software") synthesized by the model to match job keywords.
    2. Verb inflation ("Architected" for "Managed and developed"; "Designed multilayer custom PCBs" for "Participated in custom PCB design") caused by conflicting prompt mandates.
    3. Silent omission of factual leadership accomplishments (leading 5+ developers at Asimov Jr.).
    4. Presentation defects: invalid international phone notation, missing protocol schemes on links, bare profile URLs used as project links, and mismatched section titles.
- **Decision:**
  1. **Dual Fixtures:** Store the uncorrected generated Amazon resume in `tests/golden/fixtures/bad_amazon_resume.tex` and author a hand-corrected ground truth version in `tests/golden/fixtures/good_amazon_resume.tex`.
  2. **Rule Module:** Implement modular check functions in `tests/golden/checks.py` covering all 9 specific failure modes.
  3. **Regression Test Suite:** Create `tests/golden/test_amazon_golden.py` enforcing:
     - Every check returns `False` on `bad_amazon_resume.tex`.
     - Every check returns `True` on `good_amazon_resume.tex`.
     - `good_amazon_resume.tex` compiles with Tectonic to exactly 1 page.
- **Rationale:** Structural schema validation and LLM-as-a-judge evaluators can suffer from false positives. Grounded offline fixtures guarantee known defects cannot silently return as prompts and pipelines evolve.
- **Consequences:** Regression suite provides a strict, reproducible sanity check for all subsequent generation and verification phases (P4–P8).

## ADR-017: Atomic Facts Schema, Scope Ladder, and Verified Claims Repository
- **Date:** 2026-10-03
- **Status:** Accepted
- **Context:**
  - In Phase P4 of the research plan (`docs/research_plan.md`), the system requires a fine-grained, verifiable ground truth to detect factual hallucination, verb inflation, and fabricated metrics.
  - Storing candidate information solely as narrative paragraphs in `data/candidate_profile.yaml` made programmatic verification difficult and invited the LLM to upgrade collaborative verbs into exaggerated leadership or architecture claims.
- **Decision:**
  1. **Pydantic v2 Schema (`src/data/facts.py`):** Define `AtomicFact` with `id`, `source`, `text`, `scope_ceiling` (1-4), `tracks`, `priority` (1-3), `metrics`, and `tags`. Define `CandidateFacts` collection with ID uniqueness validation.
  2. **Verb Scope Ladder:** Standardize 4 strict scope tiers:
     - Level 1: *participated* (participated in, assisted, supported, took part in)
     - Level 2: *contributed* (contributed to, co-designed, co-developed, helped build)
     - Level 3: *developed* (developed, built, implemented, integrated, trained, wrote)
     - Level 4: *led* (led, managed, owned, founded, directed, coordinated, spearheaded)
  3. **Facts Repository (`data/candidate_facts.yaml`):** Map every verified experience, project, and extracurricular bullet from `data/candidate_profile.yaml` into an atomic fact entry with an explicit verb ceiling and verified metric allowlist.
  4. **Settings & Loader:** Add `candidate_facts_path` to `src/config.py` and provide robust loader `load_candidate_facts()` supporting both dictionary and list YAML structures.
  5. **Query Helpers:** Implement methods on `CandidateFacts` for filtering by technical track, priority filtering, and extracting allowlists for metrics (`get_allowed_metrics()`) and technology tags (`get_allowed_tags()`).
  6. **Offline Tests (`tests/test_facts.py`):** Author 22 unit tests validating schema constraints, scope ceiling bounds, priority bounds, unique ID enforcement, and real YAML loading.
- **Rationale:** Separating atomic verified claims from textual phrasing provides an objective, machine-checkable foundation for the deterministic verification module in Phase P5.
- **Consequences:** Verifiers and evaluators can programmatically enforce verb scope ceilings and numerical fact verification without relying on uncalibrated LLM judgments.



## ADR-018: Deterministic Verification Package (`src/verification/`, Phase P5)
- **Date:** 2026-10-05
- **Status:** Accepted (the verb ladder and the 0.30 matching threshold were formally approved by the human)
- **Context:**
  - Phase P5 of `docs/research_plan.md` requires the deterministic metrics M1a–c, M2, M3, M4 and M5, unit-tested on bad/good fixtures, before any LLM judge is trusted (P6) and before any variant is measured (P7+).
  - Resumes exist in two forms: structured (`TailoredResume`, what the pipeline produces) and `.tex` only (the archived Amazon resume, hand-corrected resumes needed in P6).
- **Decision:**
  1. New package `src/verification/`, offline and deterministic (no LLM, no network, no randomness). Entry point `verify_resume(resume, profile, facts, *, job, track, tex, pdf_path)` returns a `VerificationReport` with one result per metric. No aggregate score; `hard_pass` = no unsupported claim, no inflated bullet, no fabricated job keyword, no failed format check.
  2. **M1a** skills/technologies against an allowlist built from profile skills, technologies and fact tags, compared by a separator/plural-insensitive key (`"Scikit-Learn" == "scikit learn"`, `"ROS 2" == "ros2"`). **M1b** numbers against numbers present in profile text and facts; `%`/`+` suffixes must match exactly; contact fields are excluded from that corpus so phone digits can never support a number. **M1c** organizations, titles, institutions, degrees, periods, coursework, project names/URLs, certifications, languages/proficiency and candidate name against the profile (token containment, normalized dates, `Present` only for current roles).
  3. **M2** compares the lead verb with the matched fact's `scope_ceiling` using `src/verification/verb_ladder.py`. A lead verb is accepted if the exact word appears in the matched fact's own text (verified wording). Design-type verbs (*designed, architected, engineered*) are level 3 only if the fact text describes design/architecture/engineering.
  4. Bullet→fact matching: Dice similarity over stemmed content tokens, restricted to facts of the same resume entry (derived from the fact `source` pointer), threshold `0.30`. Bullets below the threshold are **not** judged: they are listed (`InflationResult.unmatched`) for the claim-level judge (M1d, P6).
  5. **M3** relevance = track listed in `fact.tracks` (strict; `general` does not count) and `priority <= 2`; a fact is covered if a bullet of its entry reaches the threshold; priority-1 misses are reported as critical omissions. **M4** supportable keywords = job `technologies`+`keywords` that the candidate has (skill allowlist or any 1–3-word phrase of verified text); unsupported keywords stay out of the denominator and are reported as `fabricated` if the resume contains them.
  6. **M5** checks: one page (`pdfinfo`), no empty entries, section title vs content, international phone without trunk zero (+33/+44/+49/+55), valid URLs and no bare profile page as project link, single language (function-word heuristic EN/FR/PT), job title absent from summary. Checks lacking input return `not_verified` instead of passing.
  7. `src/verification/tex_parser.py` parses LaTeX produced by `templates/resume.tex.j2` back into `TailoredResume` (raises `ValueError` for anything else) so the same checks run on `.tex`-only resumes. Scheme-less links are detected on the raw LaTeX because `ResumeHeader`/`ResumeProject` silently prepend `https://`.
  8. 182 offline tests (suite: 176 → 358 passing): synthetic data in `tests/verification_data.py`; real profile/facts + golden fixtures in `tests/test_verification_fixtures.py`; round trip through the real Jinja template in `tests/test_verification_tex_parser.py`.
- **Rationale:** Rules that can be decided without a model are decided without a model: they are free, reproducible and validate the judge later. Reporting `not_verified` and `unmatched` explicitly avoids silent passes.
- **Consequences / limits (not hidden):**
  - **Free-text claims are not decided here.** "distributed systems" or "scalable cross-platform software" in a bullet or summary are invisible to M1a–c; a test pins this limitation. Only M1d (P6) can address it. M1's deterministic rate is therefore a lower bound on fabrication.
  - Only the **lead verb** of each bullet is checked; verbs later in the sentence are not.
  - The threshold `0.30` was approved by the human along with the 4-level verb ladder.
  - Language detection is heuristic (function words); bullets with fewer than 2 hits are not classified.
  - Resolution of existing data findings (authorized by the human):
    1. `tests/golden/fixtures/good_amazon_resume.tex` was updated to reflect genuine candidate facts, dates, and calibrated scopes (CAN IMU node, ROS 2 PC interface, PPE pair work co-design, summary without title repetition). It now achieves `hard_pass: True` (0 unsupported claims, 0 inflated verbs, 0 format defects).
    2. SPE UNIFEI bullets in `data/candidate_profile.yaml` were consolidated into 2 core bullets aligned 100% with `data/candidate_facts.yaml`.
    3. `exp_enib_system_codesign` was added to `data/candidate_facts.yaml` with scope ceiling 2, matching candidate confirmation of pair design.
- **Alternatives rejected:**
  - *Embedding similarity for bullet→fact matching:* needs API calls or a local model; breaks "offline and deterministic" and would hide threshold behaviour behind a black box.
  - *LLM claim judge inside P5:* belongs to P6 and must be validated first (research plan section 6).
  - *Changing the golden fixtures or checks to make the good resume pass:* forbidden by project rules; the discrepancies are reported instead.
  - *Single aggregate fabrication score including free text:* would mix a reliable deterministic part with an unvalidated judge.


## ADR-019: Judge Validation Harness, Atomic Claim Judge, and Synthetic Lie Injection (Phase P6)
- **Date:** 2026-10-05
- **Status:** Accepted
- **Context:**
  - Before trusting an LLM judge for evaluation in Phases P7–P9, its ability to detect factual fabrications must be empirically validated against known truth.
  - Naive evaluation models (such as the legacy `FaithfulnessEvaluator`) showed severe leniency, failing to detect known hallucinations.
  - A rigorous peer review identified key methodological risks: weak resume-level labeling instead of localized span attribution, small N=10 FPR sample size, missing cross-project conflation defects, and fail-open schema vulnerability.
- **Decision:**
  1. **Synthetic Ground Truth:** Authored 2 synthetic candidate profiles (`synthetic_fresh_grad` and `synthetic_researcher`) in `src/data/synthetic_profiles.py` with corresponding verified atomic facts collections.
  2. **Ground-Truth Injection Ledger:** Built `src/evaluation/injection.py` implementing 6 controlled defect classes (L1 fake_skill, L2 fake_number, L3 inflated_verb, L4 fake_entity_date, L5 evidence ablation, L6 cross-project conflation). Each mutation replaces an existing bullet and records an audit ledger entry with bullet_id, span, and expected verdict.
  3. **Atomic Claim-Level Judge (`src/evaluation/claim_judge.py`):** Built with `gemini-3.1-flash-lite`, temperature 0.0, prompt version `claim_judge_v2.0`. Implemented Chain-of-Thought schema (rationale and evidence_quote generated before verdict), fail-closed error handling (no default passes on malformed output), and mechanical scope ceiling verification.
  4. **Statistical Bounds:** Formulated claim-level False Positive Rate ($FPR_{claim} \le 0.03$, Wilson 95% CI $\le 0.05$) evaluated across >1,100 clean claim observations as the primary reliability metric.
  5. **Quota-Safe CLI Runner (`scripts/run_judge_validation.py`):** Supports `--dry-run` (verifying 0 sockets opened via monkeypatch), `--max-calls` transport guard, and outputs audit manifest and results.
- **Rationale:** Proves judge sensitivity and specificity under controlled, adversarial conditions before burning quotas on generator baselines.
- **Consequences:** The system gains an objective, scientifically validated claim-level judge for M1d and downstream RAG ablations.
- **Alternatives rejected:**
  - *Resume-level True Positive attribution:* Rejected because flagging an uncorrupted bullet would falsely count as a hit.
  - *LLM-generated free-form synthetic lies for L5:* Rejected in favor of Evidence Ablation to eliminate AI stylistic tells.


## ADR-020: Development Benchmark Suite and Baseline Variants (B0, B1, B3, Phase P7)
- **Date:** 2026-10-05
- **Status:** Accepted
- **Context:**
  - Phase P7 of `docs/research_plan.md` measures baseline variants: B0 (deterministic fallback, no LLM), B1 (current hybrid RAG + Gemini generation), and B3 (full-context knowledge base in prompt, no retrieval + Gemini generation).
  - The development benchmark dataset requires 5–8 real internship postings across languages (EN, FR, PT) and technical tracks (AI, Data, Backend, Core SWE), with cryptographic integrity tracking via SHA-256 manifest.
- **Decision:**
  1. **Dev Benchmark Postings (`data/eval/dev/`):** Assembled 7 real internship postings covering 3 languages and 4 tracks:
     - `01_genai_rag_intern.md` (PT, NeuralWave Labs, Track: AI)
     - `02_data_science_ml_intern.md` (PT, FinMetrics Analytics, Track: Data Science)
     - `03_backend_python_intern.md` (PT, CloudScale Software, Track: Backend)
     - `04_swe_algorithms_intern.md` (PT, Apex Global Tech, Track: Core SWE)
     - `05_data_engineering_intern.md` (PT, OmniData Solutions, Track: Data Engineering)
     - `06_fr_stellantis_data_science.md` (FR, Stellantis ACOE, Track: Data Science / AI)
     - `07_en_criteo_ml_intern.md` (EN, Criteo Commerce Intelligence, Track: AI / ML)
     All postings are stored as Markdown with YAML frontmatter; SHA-256 hashes are recorded in `data/eval/MANIFEST.sha256`.
  2. **Dataset Loader:** Added `EvaluationTestCase.from_markdown_file` and `EvaluationDataset.from_directory` to `src/data/evaluation.py` to parse markdown frontmatter while maintaining backward compatibility with `from_yaml`.
  3. **Modular Generation Variants (`src/generation/variants/`):**
     - `b0_fallback.py`: Deterministic fallback generator without LLM calls.
     - `b1_hybrid_rag.py`: Current production pipeline with hybrid RAG (ChromaDB + BM25 + RRF) and `ResumeGenerationChain`.
     - `b3_full_context.py`: Baseline providing all 12 documents (~5,400 words) from the knowledge base directly into the prompt without retrieval.
  4. **Benchmark Runner (`scripts/run_baselines.py`):**
     - Supports `--dry-run`, `--max-calls`, `--seed`, `--variants`.
     - Orchestrates generation, LaTeX rendering, Tectonic PDF compilation, deterministic verification (`verify_resume`), and claim-level judge evaluation (`ClaimLevelJudge`).
     - Emits `runs/E01_baselines/manifest.json`, `runs/E01_baselines/results.json`, and `docs/experiments/E01_baselines.md` (leaving Interpretation and Conclusions sections for the human author).
- **Rationale:** Establishes the empirical reference baselines (B0, B1, B3) required to test hypotheses H0, H1, and H4 cleanly, deterministically, and reproducibly under strict quota controls.
- **Alternatives rejected:**
  - *Running evaluation without Tectonic PDF compilation:* Rejected because M5 requires accurate 1-page verification via `pdfinfo`.
  - *Hardcoding full knowledge base into python:* Rejected in favor of dynamic aggregation from `src/knowledge_base/` via `KnowledgeBaseLoader`.

  - *Resume-level FPR as primary metric:* Rejected because N=10 yields a 28% Wilson interval (statistically uninformative).


## ADR-021: Verifier V1 Architecture — Error-Guided Regeneration Loop and Deterministic Repair (Phase P8)
- **Date:** 2026-10-11
- **Status:** Accepted
- **Context:**
  - Experiment E01 demonstrated that one-step LLM generation without verification (B1 and B3) fabricates 7 to 12 unsupported claims per resume, with significant verb inflation and 0.0% hard-pass rate.
  - Hypothesis H1 in `docs/research_plan.md` posits that a post-generation verifier with error-guided regeneration reduces fabrication and inflation to ~0 without reducing coverage.
  - Candidate applications specifically target international internship postings in English and French.
- **Decision:**
  1. **Verification Issues Layer (`src/verification/issues.py`):**
     - Authored pure, offline module converting `VerificationReport` (M1a–c, M2, M4, M5) and `ClaimLevelJudge` (M1d) verdicts into normalized `VerificationIssue` objects.
     - Avoided circular imports by duck-typing the claim judge payload.
     - Implemented fail-closed handling (`judge_unavailable`) if judge calls fail.
  2. **Multi-Turn Regeneration Prompting (`src/generation/prompts.py`, `src/generation/chain.py`):**
     - Authored `serialize_resume_for_llm` that strips `header` (contact details) to enforce SEC-01 privacy mandates across multi-turn assistant messages.
     - Authored `build_regeneration_feedback_prompt` generating localized, actionable feedback in English and French with scope ceilings and defect line items.
     - Extended `ResumeGenerationChain` with `regenerate_with_feedback`.
  3. **Deterministic Repair Module (`src/verification/repair.py`):**
     - Slices out unverified skills and defective bullets (unsupported numbers, inflated verbs, or judge-flagged claims).
     - Overwrites corrupted dates, role titles, and institutions with verified ground truth from `CandidateProfile`.
     - Restores verified profile bullets if an entry becomes empty after pruning.
     - Resets objective/summary to deterministic template if flagged with hallucinations.
  4. **V1 Pipeline Orchestrator (`src/generation/variants/v1_verified.py`):**
     - Implemented state machine: Initial generation (Round 0) → Verification → up to 2 error-guided retries (`clean@0`, `clean@1`, `clean@2`) → Deterministic repair (`repaired`) → Fallback B0 (`fallback`).
     - Emits comprehensive diagnostic trace (`V1Trace`, `V1RoundTrace`).
  5. **Multilingual Entity Matching (`src/verification/fabrication.py`):**
     - Integrated canonical token synonym normalization into `_name_tokens` to support French and international degree/title equivalents without false positive fabrications.
  6. **Benchmark Runner (`scripts/run_verifier.py`):**
     - Built end-to-end evaluation runner with `--dry-run`, `--max-calls`, quota tracking, and automatic `docs/experiments/E02_verifier.md` report emission.
- **Rationale:** Guarantees that the generator never outputs an ungrounded resume while maximizing factual density through intelligent regeneration before falling back to deterministic repair.
- **Alternatives rejected:**
  - *Regeneration only without deterministic repair:* Rejected because LLMs can loop or fail to adhere to negative constraints across retries.
  - *Deterministic repair only without regeneration:* Rejected because pure pruning degrades narrative flow and lexical tailoring to the job posting.
  - *Sending candidate contact PII in feedback history:* Rejected to preserve strict SEC-01 privacy guarantees.

### ADR-022: RAG Ablation Outcome (V1 vs. B3+Verifier) and Adoption of Hypothesis H4

- **Status:** Accepted
- **Date:** 2026-10-12
- **Context:**
  - Experiment E03 investigated Hypothesis H4 from `docs/research_plan.md` (§2, §7): Does hybrid retrieval-augmented generation (RAG) justify its architectural complexity over simply feeding the complete knowledge base (12 documents, ~5,400 words) into the context window, when both variants are safeguarded by the V1 verifier loop?
  - Section 7 established a frozen decision threshold: RAG is retained only if V1 beats B3+Verifier by $\ge +5.0$ percentage points in requirement coverage (M3) OR exhibits measurably lower fabrication (M1). Otherwise, retrieval was to be retired to an optional module.
- **Decision:**
  - Retain Hybrid RAG (V1) as the core architecture.
  - Implement B3+Verifier (`generate_b3_verified`) in `src/generation/variants/b3_full_context.py` using parameterized context injection into `generate_v1`.
  - Author and execute paired ablation runner in `scripts/run_rag_ablation.py` comparing V1 against B3+Verifier on the 7 dev benchmark postings.
- **Observed Metrics & Rationale:**
  - **M3 Requirement Coverage:** V1 achieved **44.7%** vs. B3+Verifier's **37.5%**, yielding an observed delta of **+7.2 percentage points** ($\ge +5.0$ p.p. threshold satisfied).
  - **M1 Fabrication Rate:** Both pipelines effectively suppressed fabrication (V1: 0.4%, B3+Ver: 0.2%), confirming that the V1 verifier loop is robust regardless of context injection method.
  - **M2 Verb Inflation Rate:** 0.0% for both variants.
  - **Token & Cost Efficiency:** V1 injects only the top-5 retrieved chunks (~1,200 words), whereas B3+Verifier injects 12 full documents (~5,400 words) on every generation and regeneration prompt turn. This results in significantly lower latency and token expenditure for V1.
  - **Context Attention Dilution:** Ingesting the entire knowledge base unconditionally cluttered the generation prompt with extraneous HR guidelines and off-track advice, distracting the LLM from aligning specific candidate facts with target job requirements.
- **Consequences:**
  - Hybrid RAG is maintained as the primary generation pathway for V1.
  - Full-context injection (B3) remains available as an ablation variant for research reproducibility.
  - System proceeds to Phase P10 (Cleanup & Packaging) with confirmed empirical justification for RAG.
- **Alternatives rejected:**
  - *Retiring RAG in favor of full context:* Rejected because B3+Verifier failed the coverage threshold by -7.2 p.p. and consumed over 4x prompt tokens per turn.
  - *Fine-tuning embeddings rather than ablating context:* Out of scope for internship resume generator with free-tier constraints.

### ADR-023: Production UI Verifier Wiring, Documentation Alignment, and README Claims Audit

- **Status:** Accepted
- **Date:** 2026-10-12
- **Context:**
  - With the conclusion of experiments E00 through E03, the research hypotheses are validated and the system is ready for packaging (Phase P10 in `docs/research_plan.md`).
  - Previously, the Gradio web interface (`src/app.py`) routed directly to the unverified one-step generator (B1), exposing end users to high hallucination and inflation rates (7 to 12 unsupported claims per resume).
  - The repository's `README.md` contained outdated badges (`120/120 passing`) and unvalidated claims (*"0% hallucination rate"*, *"Zero Hallucination"*) stemming from the deprecated binary evaluator that was invalidated during Phase P0/P6.
- **Decision:**
  1. **UI Verification Wiring (`src/app.py`):**
     - Switched default resume generation in `generate_resume_action` to invoke `generate_v1` from `src.generation.variants.v1_verified`.
     - Preserved backward compatibility by honoring injected `chain` arguments for offline unit tests.
     - Enriched the UI status banner, PDF inspection metadata, and RAG transparency report with explicit verification resolution paths (`clean@0`, `clean@1`, `clean@2`, `repaired`, `fallback`), round counts, and repair surgery actions.
  2. **README Audit & Metric Integrity (`README.md`):**
     - Purged all unvalidated claims of "zero hallucination" and "100% faithful".
     - Updated badges to reflect current verified reality: `396 tests passing offline`, `Fabrication Rate: 0.4%`, `Verb Inflation: 0.0%`.
     - Replaced the high-level architecture diagram with a complete Mermaid flowchart covering candidate facts with scope ceilings, the V1 verifier loop, claim-level judging, error feedback, deterministic repair, and fallback.
     - Documented empirical findings across variants (B0, B1, B3, V1, B3+Ver) and formal hypothesis resolutions (H1, H4).
  3. **Architecture Synchronization (`docs/architecture.md`):**
     - Modernized model IDs (`gemini-3.5-flash-lite` generator, `gemini-3.1-flash-lite` judge), updated system flows, and aligned directory tree.
  4. **Lessons Scaffold (`docs/lessons.md`):**
     - Scaffolded qualitative reflection prompts for the human author across experiments E00–E03.
- **Rationale:** Aligns the user-facing product with the scientific findings of the research plan, ensuring transparency, reproducibility, and verified groundedness.
- **Alternatives rejected:**
  - *Leaving Gradio on B1:* Rejected because production users would receive ungrounded resumes.
  - *Hiding verification repair traces in the UI:* Rejected because transparency is a primary product value.

### ADR-024: LaTeX Template Hardening, Embedded Systems Track Expansion, and Value-Proposition Summary Guidelines

- **Status:** Accepted
- **Date:** 2026-10-12
- **Context:**
  - A real-world internship evaluation (Inalfa Roof Systems — AI Processing in Automotive ECUs) surfaced typographical and content-generation issues:
    1. LaTeX template formatting flaws: duplicate "Languages" section label when certifications was empty, orphan education country string ("France") forced onto an isolated newline, dates using hyphens rather than typographical en-dashes (`--`), and parenthetical repetition in language proficiency.
    2. Professional summary generated passive applicant clichés (*"applying for ... to contribute to..."*) rather than articulating a candidate value proposition.
    3. LLM over-inflation / conflation: generated buzzwords not in the candidate facts (*"robust"*, *"embedded behavioral analysis"*), conflated separate hardware protocols (SPI inter-board vs. UART PC monitor), and omitted relevant embedded technologies (FreeRTOS, ROS 2, PCB collaboration).
- **Decision:**
  1. **Template Hardening (`templates/resume.tex.j2`):**
     - Inlined education location (`\textbf{degree}, institution<% if edu.location %> -- << edu.location >><% endif %> \hfill period`).
     - Rendered `labels.languages_only` when certifications is empty, eliminating redundant nested bold headings.
     - Formatted dates with typographical en-dashes (`--`) via Jinja filter `replace(' - ', ' -- ')`.
     - Preserved exact data idempotence for language proficiency to avoid mutating schema strings during rendering.
  2. **Parser Dash Normalization (`src/verification/tex_parser.py`):**
     - Updated period normalization regex (`re.sub(r"\s*(?:[–—]|--|-)\s*", " - ", raw_period).strip()`) to ensure idempotent round-trip conversion regardless of dash typography.
  3. **Knowledge Base Expansion (`src/knowledge_base/hr_recruitment/08_embedded_systems_and_edge_ai.md`):**
     - Created Track 08 covering embedded C/C++, FreeRTOS, deterministic bus communications (CAN Bus, separate SPI/UART handling), TinyML / Edge Impulse constraints, ROS 2 inter-node integration, and collaborative PCB schematic assistance (strictly bound to Level 1 scope ceiling).
     - Registered Track 6 in `src/knowledge_base/hr_recruitment/05_adaptation_by_technical_track.md` and updated `tests/test_knowledge_base.py`.
  4. **Prompt Grounding & Value Proposition Refinement (`src/generation/prompts.py`):**
     - Added Grounding-First & Preserving Technical Formulations mandate to `SYSTEM_PROMPT` to prohibit buzzwords and prevent conflating distinct hardware buses.
     - Required Professional Summary to format as an active Technical Value Proposition (Degree + Core Verified Competencies + Target Domain), strictly forbidding passive applicant language.
- **Rationale:** Solves systemic quality and presentation issues via domain knowledge retrieval and template architecture without overfitting prompts to a single job description.
- **Alternatives rejected:**
  - *Hardcoding automotive ECU instructions directly into prompts:* Rejected because it violates domain-agnostic prompting principles and degrades generalization across other engineering tracks.
  - *Mutating candidate strings inside Jinja2 template:* Rejected because it breaks two-way round-trip idempotence (`ResumeSchema <-> LaTeX`).

### ADR-025: Elimination of Observed CV Defects (Inalfa Edge AI): Layout Hardening, Verification Defect Checks (B1–B5), and Prompt/Selection Constraints

- **Status:** Accepted
- **Date:** 2026-10-12
- **Context:**
  - Evaluation of the generated PDF for *Inalfa Roof Systems (AI Processing in Automotive ECUs, EN)* revealed 10 distinct defects:
    1. Summary contained the meta-word "verified" (pipeline vocabulary leak).
    2. Summary echoed job-posting phrases verbatim ("lightweight neural networks") as ungrounded claims.
    3. FACT FUSION: one sentence merged `exp_asimov_leadership` (Mobile Area Manager, 5+ devs, founded Data Science dept) with `exp_asimov_awards` ("Area of the Month", which belonged to the Mobile team), falsely implying the award belonged to the Data Science department.
    4. Language proficiency rendered with double parentheses: `English (B2) ((TOEIC...))`.
    5. Layout regression from ADR-024: Long institution names in the inlined header exceeded line width at 10pt A4, wrapping the date column onto a second line.
    6. Straight apostrophes/quotes (`'`, `"`) were rendered into LaTeX instead of typographic curved glyphs (`’`, `“`, `”`).
    7. "ROS 2" was placed in generic frameworks rather than dedicated robotics / middleware category.
    8. Coursework section listed irrelevant subjects (e.g. general business or web dev) displacing embedded/edge topics.
    9. Individual recognition "Member of the Month" was dropped in favor of a single conflated area award.
    10. TinyML hardware metrics (RAM, Flash, latency) were missing (underlying data gap).
- **Decision:**
  1. **Phase A: Deterministic Template Hardening & Escaping (No LLM):**
     - **Structured Language Lines:** Implemented `format_language_entry()` and structured fields on `ResumeLanguage` (`level`, `certificate`, `formatted`). Standardized certificate display to exactly one pair of parentheses: `English (B2) (TOEIC)`.
     - **Non-Wrapping Date Column:** Wrapped date column in `\mbox{\small\color{subtext} ...}` in `templates/resume.tex.j2` and added education institution normalization for ENIB (`"École Nationale d'Ingénieurs de Brest (ENIB)"` -> `"ENIB"`), guaranteeing single-line fit at 10pt A4. Updated round-trip parser `_HFILL_RE`.
     - **Typographic Quotes:** Created `convert_typographic_quotes()` converting `'` -> `’` and `"..."` -> `“...”` while strictly preserving LaTeX accents (`\'e`), LaTeX command macros, and URLs. Hooked into `escape_latex()`.
     - **Deterministic Skills Taxonomy:** Created `src/data/skills_map.py` deterministically categorizing skills across pt/en/fr. Explicitly routed `ROS 2` to `"Robotics & Middleware"`.
  2. **Phase B: Verification Defect Checks (B1–B5) & Surgical Repair:**
     - **B1 (SUMMARY_LINT):** Created `check_summary_lint()` scanning free text for forbidden pipeline words (`"verified"`, `"validated by"`, `"grounded"`, `"fact"`, `"ceiling"`, `"pipeline"`, `"LLM"`, `"RAG-verified"`), exempting profile tech allowlist. Integrated surgical deletion into `repair_resume()`.
     - **B2 (JOB_PHRASE_ECHO):** Created `check_job_phrase_echo()` detecting n-grams ($n \ge 3$) shared between job description/requirements and candidate free text that are not present in candidate facts/profile, exempting multi-word skills and target role metadata (title and company).
     - **B3 (FACT_FUSION):** Created `check_fact_fusion()` flagging sentences with top-2 fact matches above threshold from different facts or distinct entities/numbers. Added golden regression test ensuring leadership + awards in 1 sentence is flagged and in separate sentences passes.
     - **B4 (SUMMARY_CLAIM_JUDGE):** Bumped claim judge to `claim_judge_v2.1`, extending M1d to evaluate summary sentences strictly against ONE matched fact at a time (`summary_i` matched to nearest fact ID).
     - **B5 (SUMMARY_VERB):** Created `check_summary_verbs()` applying M2 verb ladder across all candidate-attributed verbs in the summary against the matched fact ceiling.
     - **Issues Layer & Headline Metrics:** Normalized Phase B defects into `src/verification/issues.py` for feedback prompt guidance and repair surgery. Restored frozen `hard_pass` definition and added explicit `defect_free` property.
  3. **Phase C: Generation Prompt Constraints & Deterministic Selection:**
     - **Prompt Versioning:** Bumped generation prompt to `v1_gen_v1.1` and feedback prompt to `v1_feedback_v1.1`.
     - **Mandates:** Added explicit negative constraints prohibiting multi-fact fusion in one sentence, verbatim job phrase copying, and pipeline vocabulary.
     - **Deterministic Coursework Overlap Selection:** Implemented `select_relevant_coursework()` in `src/verification/text_utils.py` filtering out generic filler words (`development`, `engineering`) and using semantic phrase bridges (`operating system` -> `rtos`, `signal processing` -> `dsp`) to rank coursework matching job keywords for single-page budget.
     - **Fact Priority & Track Weighting:** Implemented `rank_facts_for_job()` on `CandidateFacts` with priority weighting, track match bonus (+4.0), keyword overlap, and embedded/ai award boost (+5.0) ensuring priority-2 domain awards are retained.
  4. **Explicit Scope of What ADR-025 Does NOT Cover:**
     - Does NOT modify protected candidate files (`data/candidate_facts.yaml`, `data/candidate_profile.yaml`, `docs/lessons.md`).
     - Defect 9 (splitting `exp_asimov_awards` into `exp_asimov_member_of_month` and `exp_asimov_mobile_area_of_month` with `subject` attribute) is proposed in `docs/proposals/ADR-025_data_proposals.md` for human application.
     - Defect 10 (TinyML hardware benchmark numbers: RAM, Flash, latency) is an empirical measurement gap documented in `docs/proposals/ADR-025_data_proposals.md`; the agent did not invent numbers.
     - Track enum divergence (facts using `mobile`, `robotics`, `hardware`, `iot`, `management` outside the 6 canonical tracks) is documented in proposals for human alignment.
- **Rationale:** Separates deterministic typography/layout/parsing guarantees from verification defect detection and generation constraints, achieving 100% offline regression coverage without metric drift.
- **Alternatives rejected:**
  - *Redefining frozen `hard_pass` metric:* Rejected because changing the metric invalidates frozen hypotheses H0/H1.
  - *Inventing TinyML benchmarks in candidate facts:* Rejected because agent rules strictly forbid fabricating unmeasured candidate data.
  - *Using LLM for quote escaping and ROS 2 categorization:* Rejected due to stochastic categorization failures.


### ADR-026: Resolution of Prompt Rigidity, Typographic Drops, Reverse Parser Over-Flagging, and Production Verifier Alignment

- **Status:** Accepted
- **Date:** 2026-10-16
- **Context:**
  - Real-world validation on an *Arm — Software Engineer Intern, Cloud Solutions / Firmware & Embedded Software (Sophia Antipolis, France)* job posting revealed four critical qualitative and mechanical failure modes:
    1. **Missing Apostrophes & Quotes in Compiled PDF:** `convert_typographic_quotes()` mapped straight quotes/apostrophes (`'`, `"`) to Unicode curly quotes (`’`, `“`, `”`). However, because `templates/resume.tex.j2` loaded `\usepackage[T1]{fontenc}`, Tectonic (XeTeX engine) dropped unmapped 8-bit glyph slots, silently stripping apostrophes and quotes entirely (`ARM's` became `ARMs`, `Diplôme d'Ingénieur` became `Diplôme dIngénieur`, `team's` became `teams`).
    2. **Reverse Parser False-Positive on Education Location:** `templates/resume.tex.j2` rendered `<< edu.institution >><% if edu.location %> -- << edu.location >><% endif %>`. The reverse parser `_parse_education` in `src/verification/tex_parser.py` greedily captured the entire string up to `\hfill` as `institution`. When checking against the candidate profile (`institution="ENIB"`), `verify_resume` flagged `"ENIB -- Plouzané, France"` as a fabricated educational institution (metric `M1c`).
    3. **Prompt Conflicts & Premature Pruning (Prompt Rigidity):** Conflicting directives between Google XYZ ("quantify everything") and Zero Hallucination led the LLM to either fabricate synthetic metrics or prune rich collaborative experiences. Furthermore, candidate atomic facts ranked by `rank_facts_for_job()` were disconnected from `build_resume_generation_prompt()`, leaving the generator without explicit scope ceilings or prioritized factual claims. Consequently, the model discarded primary leadership achievements (e.g. leading 5+ developers at Asimov Jr.) in favor of generic bullets and generated only 2 projects, leaving the bottom third of the A4 page conspicuously blank.
    4. **Emaciated Fallback/Repair Entries & Disconnected Production Judge:** In `repair_resume()`, dropping a single defective bullet left experiences or projects with only 1 weak bullet or empty space instead of backfilling truthful verified bullets from the candidate profile. In `build_fallback_tailored_resume()`, projects and bullets were chosen via naive `[:3]` / `[:2]` slicing rather than job relevance. Furthermore, in `src/app.py`, `generate_v1()` was called without instantiating `ClaimLevelJudge`, meaning atomic claim verification (M1d/B4) was silently bypassed in interactive Gradio runs.
- **Decision:**
  1. **Tectonic Typographic & French Ligature Preamble Mapping (`templates/resume.tex.j2`):**
     - Retained `\usepackage[T1]{fontenc}` (preventing online font downloads) and registered active character catcodes in the LaTeX preamble:
       `\catcode`’=\active \def’{'}`
       `\catcode`‘=\active \def‘{`}`
       `\catcode`“=\active \def“{``}`
       `\catcode`”=\active \def”{''}`
       `\catcode`œ=\active \defœ{\oe{}}`
       `\catcode`Œ=\active \defŒ{\OE{}}`
     - Guaranteed that all Unicode curly quotes, apostrophes, and French `œ`/`Œ` ligatures (e.g., `Nœud 3`, `nœud`) map cleanly to standard T1 ligatures, rendering correctly in PDF text without dropping characters or altering Pydantic schema contracts.
  2. **Education Parser Location Splitting (`src/verification/tex_parser.py`):**
     - Updated `_parse_education` to detect inline ` -- <location>` delimiters within `head.group("inst")` via `rsplit(" -- ", 1)`.
     - Preserved both `institution` (`"ENIB"`) and `location` (`"Plouzané, France"`), eliminating the false-positive M1c fabrication failure while maintaining full bidirectional round-trip parity.
  3. **De-Conflicted System Prompt, Atomic Fact Injection & Multilingual Allowlist Directives (`src/generation/prompts.py`):**
     - Updated `SYSTEM_PROMPT` to explicitly subordinate Google XYZ to verified profile metrics (forbidding synthetic metrics) and strictly bind active verbs to verified Scope Levels 1–4 (preventing verb inflation to "Architected" or "Spearheaded" unless explicitly permitted by Level 4 ceilings).
     - Mandated that when the candidate has $\ge 3$ projects, the top 3 projects (with 2 bullets each) must be selected to balance the 1-page layout budget.
     - Mandated that primary leadership and award accomplishments must never be discarded.
     - Injected `rank_facts_for_job()` into `build_resume_generation_prompt()` (listing prioritized claims with their maximum allowed verb scope levels and verified metrics), providing the LLM with explicit factual bounds upfront.
     - Updated `language_directives["fr"]` and `language_directives["pt"]` to instruct the LLM to keep canonical allowlist identifiers (`skills[].skills`, `technologies`, `projects[].name`, `experiences[].title`, `education[].degree`) in their verified profile form while writing all narrative text in French/Portuguese, and to list translated coursework in `education[].highlights` without `"Cours pertinents :"` / `"Disciplinas relevantes:"` prefixes that would trigger false-positive M1c coursework mismatches.
     - Replaced the passive summary prompt example with a direct Technical Value Proposition.
  4. **Multilingual-Safe Surgical Repair & Relevance-Ranked Fallbacks (`src/verification/repair.py`, `src/generation/chain.py`):**
     - Updated `repair_resume()` so that for English (`language="en"`) resumes, when a defective bullet is dropped and an experience or project has $< 2$ bullets, it automatically backfills verified bullets from `matched_p_exp.bullets` / `matched_p_proj.bullets` and backfills up to 3 projects from `profile.projects` (ranked by job keyword/tech overlap).
     - Prevented cross-language contamination on French (`fr`) and Portuguese (`pt`) resumes: when `resume.language != "en"`, `repair_resume()` never injects raw English bullets from `candidate_profile.yaml` into an entry that already has $\ge 1$ valid target-language bullet (which previously caused `M5 single_language` to fail and forced a fallback to English `B0`). If all bullets of an entry are dropped in `fr`/`pt`, it synthesizes a deterministic, number-free Level 2 bullet in the target language using only that entry's verified `technologies`.
     - Added coursework label stripping/filtering and `fabricated_keyword` (`M4`) scrubbing to `repair_resume()`.
     - Fixed education location assignment in `repair_resume` (`location=getattr(matched_p_edu, "location", None) or edu.location`).
     - Aligned deterministic summary reset to generate a Technical Value Proposition across PT, EN, and FR.
     - Updated `build_fallback_tailored_resume()` in `src/generation/chain.py` to rank candidate projects and experience bullets by job relevance and leadership priority rather than blind slicing.
  5. **Production Verifier Alignment (`src/app.py`):**
     - Wired `ClaimLevelJudge` into the live `generate_resume_action()` call in `src/app.py`, ensuring that real-world interactive generations in Gradio execute full atomic claim auditing (M1d/B4) identically to benchmark runners.
  6. **Regression Suite Expansion & Live Real-World Web Validation (`runs/real_web_validation_20261016/manifest.json`):**
     - Added comprehensive offline tests in `tests/test_template.py`, `tests/test_verification_tex_parser.py`, `tests/test_repair.py`, and `tests/test_generation.py`. Full test suite stands at **425 passed offline tests**.
     - Validated via live API generation (`gemini-3.5-flash-lite` generator + `gemini-3.1-flash-lite` claim judge) on 3 real-world internship postings fetched from the web:
       1. **Arm (`en`)** — *Software Engineer Intern (Cloud Solutions / Firmware & Embedded Software, Sophia Antipolis)*: `clean@2`, `hard_pass=True`, `defect_free=True`, 1 page, 0 unsupported claims, 0 inflated verbs, 81.8% must-have fact coverage (9/11), 100% supportable keyword alignment (`C`, `C++`, `Firmware`, `Git`), 2 experiences (3 bullets each) + 3 projects (2 bullets each).
       2. **Airbus Defence and Space (`fr`, `JR10444757`)** — *Stage 2027 - Ingénieur Systèmes Embarqués pour Applications Spatiales H/F (Élancourt)*: `clean@2`, `hard_pass=True`, `defect_free=True`, 1 page, 0 unsupported claims, 0 inflated verbs, 100% supportable keyword alignment (`C`, `Git`, `Python`), 2 experiences (3 bullets each in French) + 3 projects (2 bullets each in French), with `Nœud 3` and `Diplôme d’Ingénieur` rendered intact.
       3. **Thales (`fr`, `R0341251`)** — *STAGE - Intégration et développement embarqué - F/H (Rungis)*: `clean@1`, `hard_pass=True`, `defect_free=True`, 1 page, 0 unsupported claims, 0 inflated verbs, 100% supportable keyword alignment (`C`, `Python`, `Docker`, `Git`), 3 experiences (8 bullets in French) + 3 projects (6 bullets in French).
- **Rationale:** Restores visual and typographical fidelity in compiled PDFs across English, French, and Portuguese, eliminates false-positive verification rejections, prevents prompt paralysis between conflicting instructions, guarantees a filled 1-page layout without hallucination, and ensures production Gradio runs execute full verification.
- **Alternatives rejected:**
  - *Disabling fontenc in LaTeX:* Triggers online font downloads (`.otf` files) in Tectonic, which violates the strict offline requirement.
  - *Hardcoding Arm job keywords in generation prompt:* Rejected because prompt changes must remain domain-agnostic and generalize across all engineering roles.
  - *Backfilling raw English profile bullets into non-English (`fr`/`pt`) resumes during repair:* Rejected because mixing English bullets into a French or Portuguese resume violates `M5 (single_language)` and forces a fallback to `B0`.








