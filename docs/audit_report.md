# Audit Report: Fact Faithfulness, Evaluator Validity, and Pipeline Integrity

**Date:** 2026-09-30  
**Audit Type:** Read-Only Codebase & Evaluation Integrity Audit  
**Target:** RAG Resume Generator (`src/`, `templates/`, `tests/`, `docs/`, `data/`, `pyproject.toml`)  
**Status:** Completed  

---

## Executive Summary

This read-only audit investigates why the resume generator produces fabricated claims (e.g., claiming "distributed systems", "scalable cross-platform software", upgrading "Managed and developed" to "Architected", and upgrading "Participated in" to "Designed"), silently drops major verified experiences (leadership at Asimov Jr., competitive programming, a Java Bluetooth project, the SPE UNIFEI board position), and yet consistently achieves **Faithfulness = 1.000** and **Answer Relevancy = 1.000** on benchmark runs.

The audit identified critical systemic flaws in the generation prompts, evaluation methodology, configuration management, and post-generation verification:
1. **The evaluator is structurally blind to summary hallucinations:** `format_resume_claims()` explicitly excludes `objective_or_summary` from the text sent to the `FaithfulnessEvaluator`.
2. **Evaluator scoring is binary and uncalibrated:** LlamaIndex's `FaithfulnessEvaluator` returns a single binary `YES/NO` verdict for the entire concatenated resume string; `result_to_score()` converts any `YES` directly to `1.000`.
3. **Generator and judge are identical:** The same LLM (`models/gemini-flash-lite-latest`) acts as both author and judge, creating a self-reinforcing bias.
4. **Direct prompt mandate conflict:** The prompt instructs the LLM to never invent facts, but simultaneously mandates vigorous verbs ("Architected", "Engineered"), the Google XYZ formula, ATS keyword integration from the job, and a strict 1-page budget that forces truncation of legitimate experiences.
5. **Zero post-generation verification:** No module or unit test in the entire repository compares generated skills, numbers, roles, or organizations against the candidate profile.
6. **Data privacy violation:** Candidate contact data (email, phone, address, profile links) is sent in plain text to the external LLM API on every generation run.

---

## Section-by-Section Audit Responses

### A. Faithfulness

#### 1. Fact Trace from `candidate_profile.yaml` to Final PDF
**Trace of Experience #2 (`Asimov Jr.`):**
- **Ground Truth (`data/candidate_profile.yaml:88-106`):**
  - Title: `"Mobile Development & Data Science Manager"`
  - Organization: `"Asimov Jr."`
  - Bullet 1: `"Promoted from Mobile Developer to Mobile Area Manager (leading 5+ developers) and spearheaded the creation of the Data Science department from scratch. Awarded 'Member of the Month' and led the mobile team to win 'Area of the Month' for outstanding performance."`
  - Bullet 2: `"Managed and developed cross-platform mobile applications (Flutter, Dart, MongoDB), including a compliance and tracking system with REST APIs for agricultural processing, and a field data collection app for APERAM. Successfully delivered all projects with positive client reception."`
  - Bullet 3: `"Structured the Data Science area, developing training materials for new members. Delivered the department's first commercial project: automating spreadsheet data processing and generating business insights for a consulting firm using Python (Pandas, NumPy) and Power BI."`

**Points of Alteration, Omission, and Invention:**
1. **Ingestion (`src/data/candidate.py:191-209`):** Loaded accurately into `CandidateProfile`.
2. **Prompt Construction (`src/generation/prompts.py:74-100`):** `candidate.model_dump()` serialized to JSON and placed verbatim into the prompt.
3. **LLM Generation (`src/generation/prompts.py:22-49`, `src/generation/chain.py:426-444`):**
   - **Omission:** The prompt imposes a strict limit: *"Experience: Maximum 2-3 concise bullets per role"* and *"Projects: Select ONLY the top 2-3 most relevant projects"* (`src/generation/prompts.py:44-46`). The model drops Bullet 1 entirely (omitting the candidate's leadership of 5+ developers and awards) and drops the SPE UNIFEI role entirely.
   - **Verb Inflation:** `SYSTEM_PROMPT` Mandate 3 (`src/generation/prompts.py:27-30`) orders: *"Start EVERY bullet point with a vigorous, domain-specific active verb in the past tense (e.g., 'Architected', 'Engineered')... Eliminate weak, passive phrases like 'Assisted with', 'Responsible for', or 'Worked on'"*. The model upgrades Bullet 2 from `"Managed and developed"` to `"Architected cross-platform mobile compliance and tracking applications..."` (`output/resume_2027_software_dev_engineer_int_20260929_114118.tex:104`).
   - **Invention in Summary:** In the generated `objective_or_summary`, the model synthesizes: *"Proficient in Python, C/C++, and distributed systems, with a proven record of building scalable cross-platform software..."* (`output/resume_2027_software_dev_engineer_int_20260929_114118.tex:70`). Neither "distributed systems" nor "scalable cross-platform software" appears anywhere in `candidate_profile.yaml`.
4. **Parsing (`src/generation/chain.py:64-140`):** `parse_tailored_resume()` extracts the JSON payload. It normalizes dict keys but performs **no verification** against the candidate facts.
5. **Template Rendering (`src/data/resume.py:292-297`, `templates/resume.tex.j2:98-115`):** `TailoredResume.to_latex_context()` escapes characters and renders the altered/invented strings into LaTeX.
6. **Compilation (`src/generation/formatter.py:111-195`):** Tectonic compiles the LaTeX into `output/resume_...pdf` without any semantic validation.

#### 2. `FaithfulnessEvaluator` Inputs, Granularity, and Model Identity
- **Exact text received as `response` (`src/evaluation/runner.py:84-86`, `src/evaluation/benchmark.py:278, 288`):**
  Receives `sample.faithfulness_response()`, which is `claims_text` produced by `format_resume_claims(tailored_resume)` (`src/evaluation/benchmark.py:171-200`).
  > **CRITICAL FLAW:** `format_resume_claims()` extracts education, experiences, projects, skills, languages, and certifications, but **completely omits `resume.objective_or_summary`** (`src/evaluation/benchmark.py:184-200`). Therefore, fabricated claims in the summary (such as "distributed systems" and "scalable cross-platform software") are never sent to the evaluator.
- **Exact text received as `contexts` (`src/evaluation/runner.py:88-95`, `src/evaluation/benchmark.py:279, 285`):**
  Receives `[sample.candidate_facts]`, which is the plain text formatted by `format_candidate_facts(candidate)` (`src/evaluation/benchmark.py:37-116`).
- **Granularity of Verdict:**
  **Single YES/NO for the whole resume.** LlamaIndex's native `FaithfulnessEvaluator` sends the full concatenated text to the LLM judge with a prompt asking whether the response is supported by the context. It returns a single boolean flag `result.passing`. In `src/evaluation/metrics.py:128`, `result_to_score()` converts `result.passing` into `1.0` if `True` and `0.0` if `False`. There is no per-claim decomposition, no atomic proposition extraction, and no fractional scoring.
- **Judge LLM vs. Generator LLM:**
  **They are the exact same model.** In `src/evaluation/benchmark.py:234` and `src/evaluation/benchmark.py:240`:
  ```python
  self._chain = ResumeGenerationChain(llm=get_gemini_llm())
  self._runner = EvaluationRunner(llm=get_gemini_llm())
  ```
  Both call `get_gemini_llm()` with default arguments, resolving to `settings.gemini_model` (`models/gemini-flash-lite-latest` via `src/generation/chain.py:161`). The generator and judge are identical, violating ADR-001 and project research rules.

#### 3. `RelevancyEvaluator` Inputs and Evaluation Dynamics
- **Exact text received as `query` and `response` (`src/evaluation/runner.py:243-248`):**
  - `query`: `sample.query`, which is `job.to_search_query()` (`src/data/job_posting.py:59-87`), containing the job title, company, requirements, and tech stack.
  - `response`: `sample.generated_response`, which is `format_resume_as_text(tailored_resume)` (`src/evaluation/benchmark.py:119-169`).
  - `contexts`: `sample.relevancy_contexts()`, which is `retrieved_contexts` (the knowledge base chunks).
- **Could it ever return NO?**
  **Virtually impossible.** The resume generator is explicitly prompted with the job description and instructed to tailor the resume to that exact role and company (`src/generation/prompts.py:31-34, 101`). Because the generated resume contains the target job title, company name, and explicit job keywords, LlamaIndex's `RelevancyEvaluator` asks the judge: *"Does the response answer the query?"* The LLM judge sees that the resume is targeted to the query terms and returns `YES` (`1.000`). It does not measure whether the candidate actually possesses the relevant qualifications; it only checks lexical/semantic overlap between the resume and the job query.

#### 4. Post-Generation Fact and Skill Verification
- **Status:** **NOT FOUND**.
- **Evidence:** Searching `src/` confirms no verification module exists (e.g., `src/verification/` does not exist). In `src/generation/chain.py:64-140`, `parse_tailored_resume()` validates Pydantic schema structure and normalizes dictionary keys, but does not compare extracted entities against `candidate_profile.yaml`. There is no comparison of numbers (metrics), skills, organization names, dates, or action verbs against ground truth.

---

### B. Selection and Length

#### 5. Decision on Experiences/Projects and 1-Page Limit Enforcement
- **Who decides which experiences/projects/bullets appear?**
  **The LLM.** In `src/generation/prompts.py:44-46, 105-107`, the prompt instructs the LLM:
  - *"Experience: Maximum 2-3 high-impact bullets per role."*
  - *"Projects: Select ONLY the top 2-3 most relevant projects. Maximum 2 bullets per project."*
  - *"Education: Maximum 1 concise line of relevant coursework or honors per degree..."*
  The LLM autonomously decides which experiences and projects to retain or discard.
- **Where is the 1-page limit enforced?**
  - **Prompt:** Enforced as a soft directive in `SYSTEM_PROMPT` (`src/generation/prompts.py:40-48`) and `build_resume_generation_prompt` (`src/generation/prompts.py:103-111`).
  - **Template:** Enforced via LaTeX geometry and spacing parameters in `templates/resume.tex.j2:6, 37, 40-47` (`margin=0.46in, top=0.40in, bottom=0.40in`, `\titlespacing*{\section}{0pt}{4.5pt}{2.5pt}`, `itemsep=0.8pt`).
  - **Code:** **NOT ENFORCED**. In `src/generation/formatter.py:111-195`, `ResumeFormatter.compile_pdf()` executes Tectonic via `subprocess.run()`. It does not check page count, does not inspect `pdfinfo`, and has no retry or adaptive spacing logic if the output spans 2 or more pages.

#### 6. Conflict Between Mandates in `SYSTEM_PROMPT`
- **Text forbidding invention:**
  - `src/generation/prompts.py:16-20`:
    > *"1. ABSOLUTE TRUTHFULNESS & ZERO HALLUCINATION (CRITICAL):*  
    > *- You MUST ONLY use factual details, experiences, dates, institutions, projects, metrics, and technologies explicitly present in the provided Candidate Profile.*  
    > *- NEVER invent, assume, inflate, or extrapolate experiences, companies, degrees, grades, project names, or skills that the candidate did not report.*  
    > *- Any hallucinated credential will cause immediate disqualification in technical interviews.*  
    > *- If the candidate lacks a specific qualification requested in the job, highlight their closest related real competency and solid foundational coursework instead of fabricating claims."*
  - `src/generation/prompts.py:191`:
    > *- "NEVER invent experiences or qualifications not in the Candidate Verified Profile."*
- **Text pushing toward strong verbs, XYZ formula, and keyword integration:**
  - `src/generation/prompts.py:22-34`:
    > *"2. THE GOOGLE XYZ ACHIEVEMENT FORMULA:*  
    > *- For all bullet points in Experience and Projects, frame achievements using Google's formula: 'Accomplished [X] as measured by [Y], by doing [Z]'*  
    > *- Quantify results wherever technical metrics exist (e.g., latency reduction, test coverage, model accuracy/F1, dataset scale, response time).*  
    > *3. HIGH-IMPACT ACTION VERBS:*  
    > *- Start EVERY bullet point with a vigorous, domain-specific active verb in the past tense (e.g., 'Architected', 'Engineered', 'Implemented', 'Optimized', 'Benchmarked', 'Containerized')...*  
    > *- Eliminate weak, passive phrases like 'Assisted with', 'Responsible for', or 'Worked on'.*  
    > *4. CONTEXTUAL ATS & KEYWORD ALIGNMENT:*  
    > *- Integrate the explicit technologies, frameworks, and requirements from the job description naturally into the bullet points and skills categories.*  
    > *- Prioritize candidate skills and projects that have the strongest technical overlap with the job posting."*
- **Conflict Assessment:**
  **Direct, irreconcilable conflict.** Mandate 3 commands the model to eliminate phrases like "Assisted with" or "Worked on" and replace them with verbs like "Architected" or "Engineered". If a candidate wrote `"Participated in custom PCB design"` (`candidate_profile.yaml:79`), following Mandate 3 forces the LLM to upgrade it to `"Designed multilayer custom PCBs"` (`output/...tex:113`). Mandate 4 instructs the model to "integrate explicit technologies and requirements from the job description naturally into bullet points", encouraging keyword injection. When placed between Mandate 1 (do not extrapolate) and Mandates 2, 3, and 4 (upgrade verbs, quantify metrics, inject job keywords), the LLM consistently chooses stylistic enhancement over literal truth.

#### 7. Transmission of Candidate Contact Data to the LLM
- **Evidence:** `src/generation/prompts.py:74-75, 88-90`:
  ```python
  candidate_data = candidate.model_dump(exclude_none=True)
  candidate_json = json.dumps(candidate_data, indent=2, ensure_ascii=False)
  ```
  `candidate.contact` (`full_name`, `email`, `phone`, `location`, `linkedin_url`, `github_url`, `portfolio_url` from `src/data/candidate.py:22-32`) is dumped in plain text into `candidate_json` and transmitted across the network to Google's Gemini API inside `messages` (`src/generation/chain.py:426-435`).
- **Violation:** Directly contradicts `GEMINI.md`: *"Contact data (phone, email, links) must not be sent to an LLM. Once render-time injection is implemented (phase P8), this is enforced by tests. Until then, do not add new code paths that send it."*

---

### C. Retrieval

#### 8. Query Language, Knowledge Base Language, and BM25 Impact
- **Query Produced by `to_search_query()` (`src/data/job_posting.py:59-87`):**
  Generates a multi-line string:
  ```
  Job: {title} at {company}
  Technologies: {technologies}
  Requirements: {requirements[:5]}
  Keywords: {keywords[:5]}
  ```
- **Language of Query vs. Knowledge Base:**
  - Query: Field labels (`Job:`, `Technologies:`, `Requirements:`, `Keywords:`) are English, but the actual content values (`title`, `requirements`, `keywords`) are in the language of the job posting (Portuguese for the 5 benchmark cases; French for French postings).
  - Knowledge Base: All 12 documents in `src/knowledge_base/` (`01_resume_structure_for_internships.md`, `01_what_recruiters_look_for_in_interns.md`, etc.) are written **100% in English** (translated during ADR-006).
- **Expected Effect on BM25:**
  **BM25 fails completely on cross-lingual vocabulary.** BM25 is an exact lexical matching algorithm (`src/retrieval/retriever.py:33-40`). A Portuguese query containing terms like *"Estágio"*, *"Engenharia"*, *"Desenvolvimento"*, *"Requisitos"* has zero token overlap with English knowledge base documents containing *"Internship"*, *"Engineering"*, *"Development"*, *"Requirements"*. The only tokens that match are shared technical keywords (e.g. `Python`, `Docker`, `SQL`). For French job postings, French tokens (*"stage"*, *"conception"*, *"compétences"*) similarly have zero BM25 overlap with English text. While dense vector embeddings (`gemini-embedding-001`) offer cross-lingual semantic alignment, BM25 provides zero signal for non-English domain terms.

#### 9. Benchmark Job Postings and Post-Benchmark Additions
- **Are all benchmark postings synthetic Portuguese postings?**
  **Yes.** `data/eval/evaluation_dataset.yaml:13-205` contains exactly 5 test cases (`genai_rag_intern`, `data_science_ml_intern`, `backend_python_intern`, `core_swe_systems_intern`, `data_engineering_intern`), all with Portuguese titles and descriptions.
- **Knowledge Base documents added after seeing benchmark results (ADR-010):**
  Per `docs/decisions_log.md:80-90` (ADR-010), after observing low context precision in Task 5.2 (Data Engineering at 0.375 and Core SWE at 0.625), two documents were added:
  - `src/knowledge_base/hr_recruitment/06_data_engineering_internships.md`
  - `src/knowledge_base/hr_recruitment/07_systems_and_core_swe_internships.md`
  Additionally, `src/knowledge_base/hr_recruitment/05_adaptation_by_technical_track.md` was rewritten to cover those tracks.

---

### D. Configuration and Data

#### 10. Default Generation and Judge Models vs. ADR-001 & `-latest` Aliases
- **`src/config.py:38`:** `default="models/gemini-flash-lite-latest"`
- **`.env.example:5`:** `GEMINI_MODEL=models/gemini-3.8-flash`
- **ADR-001 (`docs/decisions_log.md:7`):** Specifies `Google Gemini (models 2.5 Flash and Pro)`.
- **Match Assessment:**
  Neither `config.py` nor `.env.example` matches ADR-001. Neither matches the research plan's pinned configuration (`GENERATION_MODEL=gemini-3.5-flash-lite`, `JUDGE_MODEL=gemini-3.1-flash-lite`).
- **Use of `-latest` aliases:**
  **Yes, present in multiple files:**
  - `src/config.py:38`: `models/gemini-flash-lite-latest`
  - `src/generation/chain.py:161`: Hardcoded silent override to `"models/gemini-flash-lite-latest"`
  - `src/app.py:562, 566`: Dropdown includes `"models/gemini-flash-lite-latest"` and `"models/gemini-flash-latest"`
  This violates the rule in `GEMINI.md`: *"Use pinned model IDs from settings. Never use -latest aliases. Never hardcode model IDs outside src/config.py."*

#### 11. Profile File Loaded by the Benchmark vs. App
- **Which file is loaded by the benchmark?**
  `src/evaluation/benchmark.py:360-364, 393` loads `data/candidate_profile.yaml` via CLI default.
- **Which file is loaded by the app?**
  `src/app.py:74-75, 354, 466` loads `settings.candidate_profile_path`, which defaults to `data/candidate_profile.yaml` (`src/config.py:71-74`).
- **Does its content match?**
  Both load `data/candidate_profile.yaml`. However, **the benchmark test cases in `data/eval/evaluation_dataset.yaml` do not match the profile**.
  - In `data/eval/evaluation_dataset.yaml:29`, test case `genai_rag_intern` specifies ground truth: *"Deve priorizar o projeto 'Gerador de Currículos com RAG' e a Iniciação Científica em IA e NLP."*
  - But `data/candidate_profile.yaml` was updated with the user's real background (ENIB, Master SIIA, Asimov Jr., SPE UNIFEI, CAN Bus, ROS 2, TinyML, Bluetooth). The projects and experiences expected by the benchmark test cases no longer exist in the candidate profile.

#### 12. Generation Temperature and Run-to-Run Determinism
- **Settings:**
  - `src/config.py:42`: `gemini_temperature: float = Field(default=0.2)`
  - `src/generation/chain.py:165`: `resolved_temp = temperature if temperature is not None else settings.gemini_temperature`
- **Can two runs on the same input differ?**
  **Yes.** With temperature = 0.2 (non-zero), sampling is stochastic. Repeated generations on the exact same candidate profile and job posting produce differing phrasing, varying action verbs, different selections of bullet points, and differing resume length. There is no seed parameter configured in API calls (`src/generation/chain.py:169-173`).

---

### E. Reuse and Technical Debt

#### 13. Deterministic No-LLM Baseline (`build_fallback_tailored_resume`)
- **Can it serve as a baseline?**
  **Yes.** `build_fallback_tailored_resume()` (`src/generation/chain.py:236-391`) takes `(candidate, job, language)` and constructs a fully formed, factual `TailoredResume` using deterministic Python slicing and string formatting.
- **What is needed to integrate it into the benchmark?**
  1. Add a `--baseline` / `--no-llm` flag to `src/evaluation/benchmark.py:main()`.
  2. In `EvaluationBenchmark.run_test_case()`, if baseline mode is active, call `build_fallback_tailored_resume()` instead of `chain.generate()`.
  3. Implement deterministic project ranking: currently, it takes `candidate.projects[:3]` blindly (`src/generation/chain.py:302`). Adding keyword/tech-stack intersection scoring would allow deterministic selection of the 3 most relevant projects.
  4. Pass the resulting `TailoredResume` through `format_resume_as_text()`, `format_resume_claims()`, and evaluate it via `EvaluationRunner`.

#### 14. Inconsistencies Between Documentation and Code
1. **`pdflatex` vs `Tectonic`:**
   - `docs/decisions_log.md:23` (ADR-003) and `docs/architecture.md:38` state `pdflatex` and require `texlive`.
   - `docs/architecture.md:18`, `README.md:19`, `Dockerfile:17`, and `src/generation/formatter.py:151-169` use `Tectonic`.
2. **Retrieval Candidate Pool (`top-5` vs `top-8`):**
   - `docs/architecture.md:32` states *"Top-5 relevant chunks"*.
   - `docs/decisions_log.md:86` (ADR-010) states candidate pools were increased to 8 (`similarity_top_k=8`, `bm25_top_k=8`).
   - `src/retrieval/pipeline.py:46-47` defaults to `similarity_top_k=8` and `bm25_top_k=8`.
3. **Python Version Specification:**
   - `docs/architecture.md:13` states `Python 3.11+`.
   - `pyproject.toml:11` specifies `requires-python = ">=3.11"`.
   - `Dockerfile:1` uses `python:3.12-slim`.
4. **Tested Count in README:**
   - `README.md:21` displays badge `tests-120/120 passing`.
   - Current test suite contains **127 tests** (`pytest` run on 2026-09-29).
5. **Claims of "Zero Hallucination":**
   - `README.md:22, 25` advertises `Faithfulness-1.000 (Zero Hallucination)` and `0% hallucination rate`.
   - Directly violates the research rule in `GEMINI.md`: *"Never write claims such as 'zero hallucination', '100% faithful' or 'production ready' in code, docs, README or badges unless a validated metric supports them."*

#### 15. Template and Data Bugs
1. **Mismatched Section Title when Certifications is Empty (`templates/resume.tex.j2:169-182`):**
   - When `languages` is populated and `certifications: []` (as in `candidate_profile.yaml:232`), the template renders:
     `\section{Languages & Certifications}` (or `Idiomas & Certificações`), followed only by `\textbf{Languages:}` with no certifications. The header falsely promises certifications that do not exist.
2. **Invalid International Phone Format (`data/candidate_profile.yaml:12`):**
   - Formatted as `"+33 07 43 52 84 87"`. In French international dialing, the leading `0` is dropped after `+33`. The correct international format is `"+33 7 43 52 84 87"`.
3. **Project Link Points to User Profile Instead of Repository (`data/candidate_profile.yaml:157`):**
   - Project `"TinyML: Connected Bovine Collar"` specifies `url: "https://github.com/SamuelLoureiro"`. This links to the user's general GitHub profile, not the project repository or demo.
4. **Missing URL Scheme (`https://`) on Profile Links (`data/candidate_profile.yaml:14-15`, `templates/resume.tex.j2:60-65`):**
   - Links are stored as `"linkedin.com/in/..."` and `"github.com/..."` without `https://`.
   - The template renders `\href{<< header.linkedin_url >>}{LinkedIn}`. In PDF readers, `\href{linkedin.com/...}` is interpreted as a relative local file path, causing a broken file lookup instead of opening the URL in a browser.

#### 16. Test Suite Content Truth vs. Structure
- **Assessment:** **No test asserts anything about the TRUTH of generated content.**
- **Inventory of Tests:**
  - `tests/test_schemas.py`: Asserts Pydantic validation, character escaping, and dictionary keys.
  - `tests/test_template.py`: Asserts Jinja2 renders expected LaTeX command tokens (`\documentclass`, `\section`).
  - `tests/test_generation.py`: Asserts JSON parsing, prompt string composition, and mock LLM calls. Tests compilation via Tectonic without checking PDF contents.
  - `tests/test_edge_cases.py`: Asserts graceful handling of adversarial inputs, empty inputs, and special characters.
  - `tests/test_evaluation_dataset.py`: Asserts dataset YAML loading and formatting helper output.
  - `tests/test_evaluation.py`: All evaluator calls are mocked with `MagicMock(score=1.0)`.
- No test in the repository evaluates whether an un-mocked LLM generation invented facts, altered verb scope, or hallucinated technologies.

---

## Detailed Findings Table

| ID | File:Line | Severity | Evidence | Proposed Fix | Effort |
|:---|:---|:---:|:---|:---|:---:|
| **SEC-01** | `src/generation/prompts.py:74-75, 88-90` | **HIGH** | Plain text candidate contact info (`candidate.contact`) serialized to JSON and sent to external Gemini API. | Strip contact data before prompt serialization; inject via Jinja2 render-time context in `formatter.py`. | **S** |
| **VAL-01** | `src/evaluation/benchmark.py:171-200` | **HIGH** | `format_resume_claims()` excludes `objective_or_summary`, hiding summary hallucinations from `FaithfulnessEvaluator`. | Include `objective_or_summary` in `format_resume_claims()` or evaluate it in a dedicated summary faithfulness check. | **S** |
| **VAL-02** | `src/evaluation/metrics.py:112-128` | **HIGH** | `result_to_score()` converts binary LlamaIndex boolean `passing` flag directly to `1.0` or `0.0`. No claim-level granularity. | Implement atomic claim extraction and verify each claim against atomic facts, scoring as `supported_claims / total_claims`. | **M** |
| **VAL-03** | `src/evaluation/benchmark.py:234, 240` | **HIGH** | Generator and judge both instantiate `get_gemini_llm()` without arguments, using the exact same model. | Separate settings: `generation_model` and `judge_model`. Enforce distinct models per project research rules. | **S** |
| **PRM-01** | `src/generation/prompts.py:22-34` | **HIGH** | Prompt mandates Google XYZ, vigorous verbs ("Architected"), and keyword alignment, directly conflicting with zero-hallucination mandate. | Decouple selection from phrasing; provide fact scope ceiling and forbid upgrading collaborative verbs. | **M** |
| **VER-01** | `src/generation/chain.py:64-140` | **HIGH** | No post-generation verification step exists; LLM JSON output goes directly to LaTeX template. | Build `src/verification/` verifier checking generated skills, dates, metrics, and verbs against `candidate_facts.yaml`. | **L** |
| **RET-01** | `src/data/job_posting.py:59-87`, `src/retrieval/retriever.py:33-40` | **MEDIUM** | Non-English job queries (PT/FR) searched against an English knowledge base via BM25, resulting in zero lexical overlap. | Translate job queries to English before retrieval, or provide multilingual knowledge base documents. | **M** |
| **CFG-01** | `src/config.py:38`, `src/generation/chain.py:161` | **MEDIUM** | Model identifier uses unpinned `-latest` alias and `chain.py` hardcodes silent override to `gemini-flash-lite-latest`. | Pin exact model ID (e.g. `gemini-2.5-flash` or `gemini-3.5-flash-lite`); remove hardcoded override in `chain.py`. | **S** |
| **BEN-01** | `data/eval/evaluation_dataset.yaml:29` | **MEDIUM** | Benchmark ground truth criteria reference old mock projects ("Gerador de Currículos") no longer in candidate profile. | Re-align evaluation test cases with verified profile facts or synthetic benchmark profiles. | **M** |
| **DAT-01** | `data/candidate_profile.yaml:12` | **LOW** | French phone number formatted with invalid leading zero: `+33 07 43 52 84 87`. | Correct to `+33 7 43 52 84 87`. | **S** |
| **DAT-02** | `data/candidate_profile.yaml:157` | **LOW** | Project URL points to user GitHub profile rather than project repository. | Update URL to specific repository or set to `""`. | **S** |
| **DAT-03** | `data/candidate_profile.yaml:14-15` | **LOW** | LinkedIn and GitHub URLs omit `https://`, causing PDF reader to treat them as relative local file paths. | Prepend `https://` in profile or sanitize in `src/data/resume.py`. | **S** |
| **TPL-01** | `templates/resume.tex.j2:169-182` | **LOW** | Renders "Languages & Certifications" header when certifications list is completely empty. | Dynamically adjust title to "Languages" when certifications list is empty. | **S** |
| **DOC-01** | `README.md:21-25`, `docs/architecture.md:38` | **LOW** | "Zero hallucination" claims in README; doc references `pdflatex` while code uses `Tectonic`. | Align docs with actual code; remove unvalidated claims of zero hallucination. | **S** |

---

## Recommended Execution Order

To resolve the root causes of hallucination, restore evaluation validity, and fix data/template defects, follow this prioritized execution sequence:

1. **Phase 1: Security & Privacy Patch (Immediate - Effort: S)**
   - Strip `candidate.contact` from LLM generation prompts (`src/generation/prompts.py`).
   - Implement render-time injection of contact details in `ResumeFormatter` / Jinja2 context.
   - Fix URL schemes (`https://`) and phone formatting in `data/candidate_profile.yaml`.

2. **Phase 2: Configuration & Model Alignment (Effort: S)**
   - Remove hardcoded `-latest` overrides in `src/generation/chain.py`.
   - Update `src/config.py` and `.env.example` to support separate, pinned `generation_model` and `judge_model`.

3. **Phase 3: Template & Data Bug Fixes (Effort: S)**
   - Update `templates/resume.tex.j2` to conditionally display *"Languages"* instead of *"Languages & Certifications"* when certifications are absent.
   - Clean up inconsistencies in `docs/architecture.md` and `README.md` (`pdflatex` → `Tectonic`, test counts, remove unvalidated "zero hallucination" claims).

4. **Phase 4: Prompt & Budget Deconfliction (Effort: M)**
   - Refactor `SYSTEM_PROMPT` to remove aggressive mandates that force verb upgrading ("Architected") and keyword stuffing.
   - Separate candidate fact selection from resume phrasing: introduce a two-step generation flow or explicit fact mapping.

5. **Phase 5: Grounded Verifier & Metric Overhaul (Effort: L)**
   - Create `src/verification/` module: compare generated resume claims (entities, technologies, organizations, metrics, and verbs) against atomic facts in `candidate_facts.yaml`.
   - Update `src/evaluation/benchmark.py` and `metrics.py`: include summary in claims, replace binary LlamaIndex evaluator with atomic claim-level precision/recall scoring.
   - Integrate deterministic fallback (`build_fallback_tailored_resume`) as a benchmark baseline (`--baseline`).

6. **Phase 6: Benchmark Dataset & Retrieval Modernization (Effort: M)**
   - Update `data/eval/evaluation_dataset.yaml` to include real multi-track postings (EN, FR, PT).
   - Address cross-lingual BM25 degradation (query translation or English/multilingual query expansion).

---

## What Could Not Be Verified

1. **Live LLM API Output with Alternative Models:** Per audit instructions, no API calls were made to Gemini. The exact responses of `gemini-3.5-flash-lite` or `gemini-3.8-flash` on the current prompt could not be directly observed.
2. **Behavior on Held-Out Postings:** Per project rules, held-out datasets were not opened or referenced.
3. **Exact Token Overlap Scores on Vector vs. BM25:** Actual reciprocal rank fusion weights for live Portuguese/French queries against ChromaDB embeddings were not computed via live API embedding calls.
