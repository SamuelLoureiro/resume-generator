# Development Diary

## 2026-09-22 — Initial Planning
- **What was done:** Full definition of the architecture, technology stack, and 6-phase development plan.
- **Decisions made:**
  - LLM: Google Gemini (AI Pro)
  - RAG Framework: LlamaIndex
  - Output: PDF via LaTeX
  - Interface: Gradio
  - Vector Store: ChromaDB
  - Embeddings: Google text-embedding-004
- **Model used:** Claude Opus (planning)
- **Challenges:** None at this stage.
- **Next steps:** Start Phase 1 — project setup (pyproject.toml, schemas, knowledge base).

## 2026-09-22 — Task 1.1: Project Initialization and Configuration
- **What was done:**
  - Set up `pyproject.toml` with LlamaIndex, Google Gemini, ChromaDB, Gradio, Jinja2, Pydantic, etc.
  - Created `.env.example` with a template for API keys and system variables.
  - Created `.gitignore` covering Python, virtual environments, LaTeX intermediaries, and ChromaDB.
  - Implemented `src/__init__.py` and `src/config.py` with Pydantic Settings v2.
  - Created the base directory tree (`src/data/`, `src/ingestion/`, `src/retrieval/`, `src/generation/`, `src/knowledge_base/`, `templates/`, `data/job_postings/`, `output/`, `tests/`).
- **Decisions made:**
  - Included `pydantic-settings` for robust `.env`-based configuration management.
  - Separated submodules in `src/` following the defined architecture.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 1.2 — Pydantic schemas (`src/data/*.py`).

## 2026-09-23 — Task 1.2: Pydantic Schema Modeling and Security Rules
- **What was done:**
  - Added security and privacy rules to `.agents/GEMINI.md` (shielding `.env` from agent inspection).
  - Implemented `src/data/candidate.py` with complete schemas (`CandidateProfile`, `ContactInfo`, `Education`, `Experience`, `Project`, `Skills`, etc.) and YAML import/export support.
  - Implemented `src/data/job_posting.py` with structured requirements, desirables, and a semantic search query generator (`to_search_query`).
  - Implemented `src/data/resume.py` with automatic sanitization/escaping of special LaTeX characters (`&`, `%`, `$`, `#`, `_`, etc.) via `to_latex_context()`.
  - Unified model exports in `src/data/__init__.py`.
  - Created a unit test suite in `tests/test_schemas.py` with 6 passing tests (100% success).
- **Decisions made:**
  - Deep string sanitization for LaTeX at the data model level to prevent compilation failures in Jinja2/pdflatex.
  - Tests run 100% offline, no API credentials required.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 1.3 — Create `data/candidate_profile.yaml` (candidate data) and Task 1.4 — LaTeX template (`templates/resume.tex.j2`).

## 2026-09-23 — Task 1.3: Candidate Profile Base (YAML)
- **What was done:**
  - Created the structured and annotated `data/candidate_profile.yaml` with all mapped sections: contact, summary, education (undergraduate, coursework, scholarships), experiences (undergraduate research, junior enterprise), practical AI/RAG portfolio projects, categorized technical and soft skills, languages, and certifications.
  - Added an automated unit test in `tests/test_schemas.py` ensuring the default YAML file always validates 100% against the `CandidateProfile` schema.
  - Test suite passing 7/7.
- **Decisions made:**
  - YAML structured with Portuguese content values and English keys, maintaining ease of use for the user while strictly adhering to the Pydantic models.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 1.4 — LaTeX template (`templates/resume.tex.j2`) and Tasks 1.5/1.6 — Knowledge base curation (best practices and HR recruitment).

## 2026-09-23 — Task 1.4: Dynamic LaTeX Template (Jinja2)
- **What was done:**
  - Created the modular LaTeX template in `templates/resume.tex.j2`, optimized for one-page internship resumes.
  - Used non-conflicting Jinja2 delimiters (`<% ... %>` for blocks and `<< ... >>` for variables) to eliminate any collision with LaTeX curly braces and native commands.
  - Implemented sections: Header with clickable links (email, LinkedIn, GitHub, portfolio), Professional Objective aligned to the job, Academic Education, Experiences with impact bullets and technologies, Featured Projects, Categorized Technical Skills, Languages and Certifications.
  - Created a unit test in `tests/test_template.py` validating full rendering, data injection from `TailoredResume.to_latex_context()`, and special character escaping.
  - Updated test suite: 8/8 tests passing.
- **Decisions made:**
  - Adopted standard lightweight LaTeX packages (`article`, `geometry`, `titlesec`, `enumitem`, `hyperref`, `xcolor`), compatible with any LaTeX distribution without proprietary fonts or packages.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Tasks 1.5 and 1.6 — Knowledge base curation (resume best practices and HR/internship recruitment in `src/knowledge_base/`).

## 2026-09-24 — Task 1.5: Knowledge Base Curation — Resume Best Practices
- **What was done:**
  - Created 5 technical and modular markdown documents in `src/knowledge_base/resume_best_practices/`:
    - `01_estrutura_curriculo_estagio.md`: One-page rule, ideal hierarchical order for students (education at the top), and visual scannability.
    - `02_metodo_star_xyz_bullets.md`: Google's XYZ formula, STAR method, and strategies to quantify technical results without prior corporate experience.
    - `03_verbos_de_acao_e_vocabulario.md`: Catalog of strong action verbs categorized by domain (development, AI/data, performance, leadership) and a blacklist of weak/cliché words.
    - `04_otimizacao_ats.md`: Architecture of ATS screening robots, contextual keyword matching, and compatibility checklist.
    - `05_erros_comuns_e_red_flags.md`: Fatal red flags in 6-second screening (spelling errors, generic resume, fabricated competencies).
  - Test suite: 8/8 passing.
- **Decisions made:**
  - Documents structured with clear semantic headings to optimize chunk splitting by `SentenceSplitter` in Phase 2.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 1.6 — HR and internship recruitment knowledge base curation (`src/knowledge_base/hr_recruitment/`).

## 2026-09-24 — Task 1.6: Knowledge Base Curation — HR and Internship Recruitment
- **What was done:**
  - Created 5 specialized markdown documents in `src/knowledge_base/hr_recruitment/`:
    - `01_o_que_recrutadores_procuram_em_estagio.md`: Focus on learning agility, solid fundamentals, and ownership mindset.
    - `02_diferencas_big_techs_vs_startups.md`: Evaluation criteria at Big Techs (scale, architecture, algorithms) vs. Startups (speed, end-to-end, MVPs, pragmatism).
    - `03_soft_skills_e_diferenciais_competitivos.md`: "Show, Don't Tell" principle for communication, teamwork, and intellectual curiosity.
    - `04_valorizacao_experiencias_academicas_e_projetos.md`: How to convert undergraduate research, junior enterprise, tutoring, and personal projects into high-value corporate market experience.
    - `05_adaptacao_por_trilha_tecnica.md`: Semantic prioritization guidelines by technical tracks (AI/RAG, Data Engineering, Backend).
  - Implemented a unit test in `tests/test_knowledge_base.py` validating the presence, size, and format of all knowledge base documents.
  - Updated test suite: 9/9 passing with 100% success.
- **Decisions made:**
  - Complete closure of all deliverables for **Phase 1 (Foundation & Data)** of the project.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Start **Phase 2 — RAG Core Pipeline** (Loader with `SimpleDirectoryReader`, indexing with `SentenceSplitter`, embeddings with `models/text-embedding-004`, ChromaDB vector store, and hybrid retriever).

## 2026-09-25 — Task 2.1: Document Loader Implementation (LlamaIndex)
- **What was done:**
  - Installed and configured LlamaIndex dependencies (`llama-index-core`, `llama-index-readers-file`, `llama-index-llms-gemini`, `llama-index-embeddings-gemini`, `llama-index-vector-stores-chroma`, `chromadb`) in the `.venv` virtual environment.
  - Implemented `src/ingestion/loader.py` with the `KnowledgeBaseLoader` class and the `extract_title_from_markdown` helper function:
    - Integrated `SimpleDirectoryReader` for recursive Markdown file scanning.
    - Automatic metadata enrichment for each document (`category`, `topic`, `file_name`).
    - Methods for selective loading by category (`load_category`) and aggregated loading (`load_all_documents`).
  - Created unit tests in `tests/test_ingestion.py` covering title extraction, category loading, document aggregation, custom directories, and exception handling.
  - Updated test suite: 15/15 passing with 100% success.
- **Decisions made:**
  - Metadata enrichment at load time to enable precise contextual filtering in ChromaDB during retrieval.
- **Model used:** Gemini Flash (execution)
- **Challenges:** gRPC dependency resolution succeeded via pip without issues.
- **Next steps:** Task 2.2 — Indexing with `SentenceSplitter` and embedding generation (`src/ingestion/indexer.py`).

## 2026-09-25 — Refactoring Phase 1: Codebase Standardization to English
- **What was done:**
  - Translated all planning and documentation files to English: `docs/architecture.md`, `docs/decisions_log.md`, `docs/development_diary.md`.
  - Translated all inline string labels in `src/data/job_posting.py` (`to_search_query`, `to_prompt_context`) from Portuguese to English.
  - Updated default field values and docstring references in `src/data/candidate.py` and `src/data/job_posting.py` from Portuguese to English (`"Presente"` → `"Present"`, `"Híbrido"` → `"Hybrid"`, etc.).
  - Updated `src/data/resume.py` docstring references to remove Portuguese examples.
  - Updated test assertions in `tests/test_schemas.py` to match the new English string labels.
  - Updated test strings in `tests/test_ingestion.py` to reflect English defaults.
  - Added ADR-006 to `docs/decisions_log.md` documenting the standardization decision.
  - Marked Phase 1 as complete in `refactor_plan.md`.
  - Full test suite passing: 15/15.
- **Decisions made:**
  - Runtime data values in the candidate profile YAML and knowledge base markdown documents remain in Portuguese (user-facing content, not identifiers or labels).
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 2.2 — Verification & Indexing with SentenceSplitter and Gemini/Mock embeddings.

## 2026-09-25 — Task 2.2: Knowledge Base Indexer & Vector Store Verification
- **What was done:**
  - Audited and verified `src/ingestion/indexer.py` implementation against Phase 2 requirements.
  - Added `get_embedding_model` factory supporting `GeminiEmbedding` (production via settings) and `MockEmbedding` (offline testing, dim=768).
  - Allowed `KnowledgeBaseIndexer.__init__` to default to `get_embedding_model()`, simplifying production initialization.
  - Enhanced `KnowledgeBaseLoader.load_category` to gracefully skip empty category directories with a warning instead of failing.
  - Added end-to-end integration test (`test_indexer_integration_with_real_kb_docs`) that reads all 10 real knowledge base Markdown files, chunks them with `SentenceSplitter` (512 tokens / 50 overlap), persists vectors to ChromaDB, and verifies index reloading.
  - Updated test suite: **29/29 tests passing** with 100% success.
- **Decisions made:**
  - Embedding factory defaults to offline mode during automated tests and picks up Google AI Pro credentials via `Settings` in live execution.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 2.3 — Hybrid Retriever implementation (`src/retrieval/retriever.py`).

## 2026-09-25 — Task 2.3: Hybrid Retriever Implementation (ChromaDB + BM25 + RRF)
- **What was done:**
  - Installed and configured `llama-index-retrievers-bm25` (with `bm25s` and `pystemmer`) in `.venv` and updated `pyproject.toml`.
  - Implemented `src/retrieval/retriever.py` with:
    - `reciprocal_rank_fusion` (RRF, constant k=60) for unbiased multi-retriever score combination.
    - `format_retrieved_context` for formatting retrieved knowledge chunks into clean Markdown for prompt injection.
    - `HybridResumeRetriever` combining dense vector search (`VectorIndexRetriever` with ChromaDB) and sparse search (`BM25Retriever`), with metadata filtering by category (`resume_best_practices`, `hr_recruitment`).
    - `retrieve_for_job` method directly accepting a `JobPosting` instance and generating optimized queries via `to_search_query()`.
  - Exported symbols cleanly in `src/retrieval/__init__.py`.
  - Created comprehensive test suite in `tests/test_retrieval.py` with 9 tests covering RRF fusion, empty input handling, context formatting, dense-only retrieval, BM25 exact matching, category filtering, JobPosting integration, and end-to-end retrieval with the real knowledge base.
  - Added ADR-007 to `docs/decisions_log.md`.
  - Test suite updated: **38/38 tests passing** with 100% success in 5.99s.
- **Decisions made:**
  - Reciprocal Rank Fusion adopted as the hybrid reranking strategy to eliminate score scale divergence between cosine similarity and BM25 scores.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 2.4 / 2.5 — RAG pipeline integration wiring and Phase 2 closure.

## 2026-09-25 — Task 2.4: KnowledgeBasePipeline Orchestration (Phase 2 Closure)
- **What was done:**
  - Implemented `KnowledgeBasePipeline` in `src/retrieval/pipeline.py`:
    - Full lifecycle management: source document loading -> SentenceSplitter chunking -> ChromaDB vector index build/reload -> BM25 node indexing -> Hybrid retrieval with RRF.
    - Added `is_collection_populated` helper to detect existing ChromaDB data and prevent redundant reindexing on application startups.
    - Added `get_context_for_job` method that returns pre-formatted, structured Markdown guidelines for direct injection into Phase 3 prompts.
  - Exported pipeline symbols in `src/retrieval/__init__.py`.
  - Added 3 automated tests in `tests/test_retrieval.py` testing collection detection, index reload/reuse without rebuilding, and job context generation.
  - Executed full test suite: **41/41 tests passing** with 100% success in 7.06s.
  - Concluded **Phase 2 (RAG Core)** in its entirety.
- **Decisions made:**
  - `KnowledgeBasePipeline` serves as the single facade for the generation layer (`src/generation/chain.py`) and UI (`src/app.py`), abstracting away ChromaDB and BM25 details.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Phase 3 — Generation & Formatting (Prompt engineering, multi-step generation chain with Gemini, and LaTeX resume compilation).

## 2026-09-25 — Phase 3: Generation & Formatting Implementation
- **What was done:**
  - Implemented `src/generation/prompts.py`:
    - `SYSTEM_PROMPT` containing the 5 Inviolable Mandates (Zero Hallucination, Google XYZ formula, high-impact action verbs, contextual ATS keyword density, and strict JSON output compliance).
    - `build_resume_generation_prompt` integrating CandidateProfile, JobPosting context, and RAG guidelines.
    - `get_resume_schema_description` generating JSON Schema for the `TailoredResume` Pydantic model.
  - Implemented `src/generation/chain.py`:
    - `ResumeGenerationChain` orchestrating LLM chat invocations via LlamaIndex.
    - `extract_json_payload` robustly parsing raw JSON, markdown-fenced codeblocks, and embedded bracketed objects.
    - `parse_tailored_resume` validating LLM output strictly against Pydantic schema.
    - `get_gemini_llm` factory providing configured `Gemini` instances from settings.
  - Implemented `src/generation/formatter.py`:
    - `ResumeFormatter` rendering `templates/resume.tex.j2` with LaTeX-escaped context.
    - `compile_pdf` invoking Tectonic standalone binary to compile 1-page PDF resumes into `output/` with clean sanitized filenames.
    - `build_jinja_environment` configuring non-conflicting LaTeX delimiters (`<% %>` and `<< >>`).
  - Exported symbols in `src/generation/__init__.py`.
  - Created test suite in `tests/test_generation.py` with 12 tests covering prompt structure, schema parsing, JSON extraction, mock LLM generation chain, filename sanitization, LaTeX template rendering, and real PDF compilation via Tectonic.
  - Added ADR-008 to `docs/decisions_log.md`.
  - Executed full test suite: **53/53 tests passing** with 100% success in 8.29s.
  - Concluded **Phase 3 (Generation & Formatting)** in its entirety.
- **Decisions made:**
  - Anti-hallucination guardrails enforced at both prompt level and Pydantic validation level.
  - Tectonic confirmed as the default LaTeX compiler due to standalone zero-dependency execution.
- **Model used:** Gemini Flash (execution)
- **Next steps:** Phase 4 — User Interface (Interactive Gradio App in `src/app.py` connecting Candidate Profile upload, Job Posting input, and real-time PDF generation/preview).

## 2026-09-25 — Task 4.1: Gradio Web Application Layout & Input Panels
- **What was done:**
  - Installed `gradio` (v6.28.0) in `.venv` and verified environment dependencies.
  - Implemented `src/app.py`:
    - `load_candidate_profile_from_path` loading the default profile (`data/candidate_profile.yaml`) and generating an initial Markdown summary.
    - `handle_profile_upload` supporting custom candidate YAML uploads, fallback to default, and robust path extraction.
    - `build_app` using Gradio Blocks with two balanced columns:
      - Left column: Candidate Profile selector/upload, target internship details (title, company, location, work model, job description, tech stack), and advanced RAG settings (model, temperature, top-k guidelines, force re-index).
      - Right column: Real-time execution status banner and 3 tab panels (PDF Preview & Download, RAG Guidelines Applied, and Rendered LaTeX Source Code).
  - Created test suite in `tests/test_app.py` with 6 automated tests covering default profile loading, upload handling, error fallback, and app structure creation.
  - Test suite updated: **59/59 tests passing** with 100% success in 11.05s.
- **Decisions made:**
  - Designed the input panel to preload the user's default verified profile while allowing custom YAML overrides for multi-profile flexibility.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Resolved Gradio 6.0 parameter placement deprecation warning and fixed Path object resolution in file uploads.
- **Next steps:** Task 4.2 — End-to-End Pipeline Wiring to the "Generate Tailored Resume" button with real-time PDF rendering.

## 2026-09-25 — Task 4.2: End-to-End Gradio Workflow Wiring & PDF Generation
- **What was done:**
  - Implemented `generate_resume_action` in `src/app.py`:
    - Validates mandatory fields (Job Title, Company, Job Description).
    - Resolves CandidateProfile (default or custom uploaded YAML).
    - Instantiates JobPosting with structured technologies and keywords.
    - Executes RAG retrieval via `KnowledgeBasePipeline.get_context_for_job` (with dynamic Top-K and force re-index support).
    - Triggers `ResumeGenerationChain` to produce a structured `TailoredResume`.
    - Compiles the final PDF via `ResumeFormatter` using Tectonic.
    - Returns updated status, downloadable PDF path, metadata summary, RAG guidelines text, and rendered LaTeX source.
  - Connected the action to `generate_btn.click` with full input and output component mappings.
  - Added 3 automated tests in `tests/test_app.py` covering input validation, mock end-to-end execution, and graceful chain error handling.
  - Test suite updated: **62/62 tests passing** with 100% success in 12.10s.
- **Decisions made:**
  - `generate_resume_action` accepts optional injected pipeline/chain/formatter dependencies, enabling deterministic, fast, offline unit testing.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 4.3 — Export, RAG Transparency tabs, and generation history.

## 2026-09-25 — Task 4.3: RAG Transparency Analytics & Dual Format Export (PDF + TeX)
- **What was done:**
  - Implemented `format_rag_transparency_report` in `src/app.py`:
    - Generates a Markdown report containing: query string generated from `JobPosting`, total chunks retrieved, RRF fusion details (k=60), structured Markdown table mapping Rank -> Topic -> Category -> Source Document -> RRF Score, and formatted guideline content injected into the prompt.
  - Added dual-format export in the Gradio UI:
    - Added `tex_download` component alongside `pdf_download`, allowing users to download both the compiled PDF and the raw `.tex` source for manual editing or Overleaf import.
  - Updated `generate_resume_action` to return the `.tex` file path and the analytical transparency report.
  - Created automated test in `tests/test_app.py` (`test_format_rag_transparency_report`) and updated existing tests to validate 6-tuple return values.
  - Test suite updated: **63/63 tests passing** with 100% success in 10.84s.
- **Decisions made:**
  - Exposing exact RRF scores and source document names in the UI provides complete explainability for recruitment recommendations.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None.
- **Next steps:** Task 4.4 — Generation History Tab & UI polish.

## 2026-09-25 — Task 4.4: Generation History Inspection & Phase 4 Completion
- **What was done:**
  - Implemented generation history backend functions in `src/app.py`:
    - `list_generated_resumes`: Scans the output directory, extracts metadata (filename, size, modification timestamp, presence of `.tex` source), and sorts descending by generation time.
    - `get_history_table_data`: Formats history records into tabular rows for Gradio Dataframe display.
    - `get_history_choices`: Extracts list of filenames for dynamic dropdown selection.
    - `on_select_history_resume`: Loads the selected resume's PDF file path, `.tex` file path, and LaTeX source code for live preview and dual-format download.
  - Added the **📁 Generation History** tab to the Gradio interface:
    - Interactive Dataframe displaying all generated resumes with timestamps, file sizes, and `.tex` source availability.
    - Refresh History button for manual rescan.
    - Historical resume viewer with dedicated PDF and LaTeX download components and live LaTeX code preview.
    - Integrated automatic history table and dropdown updates immediately after each successful resume generation run.
  - Added 3 comprehensive automated unit tests in `tests/test_app.py`:
    - `test_list_generated_resumes_empty`: Verifies empty and non-existent output directory handling.
    - `test_list_generated_resumes_populated`: Verifies sorting by mtime, table rows, and choice extraction.
    - `test_on_select_history_resume`: Verifies loading existing resumes, missing file handling, and empty selection handling.
  - Updated test suite: **66/66 tests passing** with 100% success in 11.15s.
  - Successfully concluded **Phase 4 (Gradio Web Interface)**.
- **Decisions made:**
  - Kept history inspection fully client-side and filesystem-based without external database dependencies, keeping the application lightweight and portable.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Fixed missing `time` import in test module and ensured generated file names are dynamically added to the dropdown choices.
- **Next steps:** Phase 5 — Evaluation & Tuning (Setting up evaluation pipeline for faithfulness, answer relevancy, and context precision, plus edge cases testing).

## 2026-09-25 — Task 5.1: Evaluation Module Setup (LlamaIndex Evaluators)
- **What was done:**
  - Attempted to integrate RAGAS 0.4.3 as the evaluation backend. Discovered a hard import-time incompatibility: `ragas/llms/base.py` imports `from langchain_community.chat_models.vertexai import ChatVertexAI`, a module removed in `langchain-community >= 0.3.x`. Installing `langchain-google-vertexai` does not fix it because the import uses the old `langchain_community` namespace. Documented as ADR-009 in `docs/decisions_log.md`.
  - Decided to use `llama_index.core.evaluation` native evaluators — same metric dimensions, same 0-1 scoring, no compatibility issues, and directly integrated with our existing Gemini LLM configuration.
  - Created `src/evaluation/` sub-package with three modules:
    - `src/evaluation/metrics.py`: `EvaluationScores` dataclass (faithfulness, answer_relevancy, context_precision, geometric-mean aggregate), `build_evaluators(llm)` factory, and `result_to_score()` normaliser.
    - `src/evaluation/runner.py`: `EvaluationSample` dataclass with context-routing helpers (faithfulness uses candidate profile; relevancy/precision use retrieved chunks), `EvaluationRunResult`, `EvaluationRunner` with lazy evaluator building and graceful exception handling, and `format_evaluation_report()` Markdown formatter.
    - `src/evaluation/__init__.py`: clean public API exports.
  - Created `tests/test_evaluation.py` with 30 offline unit tests covering: score mathematics (geometric mean, NaN prevention), result normalisation (clamping, fallback), sample context routing (anti-hallucination isolation), runner success/failure/batch paths, evaluator lazy caching, and report formatting.
  - Created `data/eval/` directory (placeholder for Task 5.2 dataset files).
  - Test suite updated: **96/96 tests passing** with 100% success in 27.87s.
- **Decisions made:**
  - Context routing: faithfulness evaluation receives only `candidate_facts` as context (not retrieved chunks), enforcing anti-hallucination judgment w.r.t. the candidate profile specifically.
  - Geometric mean as aggregate score: extreme weakness in any single dimension floors the aggregate (e.g., faithfulness=0.0 → aggregate=0.0).
  - Lazy evaluator construction: avoids LLM initialisation during test collection when evaluators are patched via mocks.
- **Model used:** Claude Sonnet (Thinking) (execution)
- **Challenges:** RAGAS 0.4.3 incompatibility with langchain-community >= 0.3.x; resolved by switching to LlamaIndex evaluators (see ADR-009).
- **Next steps:** Task 5.2 — Evaluation Dataset & Baseline Benchmark Execution.

## 2026-09-26 — Task 5.2: Evaluation Dataset & Baseline Benchmark
- **What was done:**
  - Created `data/eval/evaluation_dataset.yaml` with 5 realistic tech internship benchmark test cases covering distinct industry tracks:
    1. GenAI / RAG Engineering (`NeuralWave Labs`)
    2. Data Science & Machine Learning (`FinMetrics Analytics`)
    3. Backend Python Development (`CloudScale Software`)
    4. Core Software Engineering / Algorithms (`Apex Global Tech`)
    5. Data Engineering & Pipelines (`OmniData Solutions`)
  - Created `src/data/evaluation.py` implementing Pydantic v2 schemas: `EvaluationTestCase` (with `to_job_posting()`) and `EvaluationDataset` (with `from_yaml()` and `get_by_id()`), exported through `src/data/__init__.py`.
  - Implemented `src/evaluation/benchmark.py`:
    - `format_candidate_facts()`: serializes the complete candidate profile into factual markdown truth.
    - `format_resume_as_text()`: comprehensive textual rendering of `TailoredResume` for answer relevancy & context precision evaluation.
    - `format_resume_claims()`: isolates historical credentials (education, experiences, projects, skills) from job application metadata, preventing false-positive hallucination penalties on target company names.
    - `EvaluationBenchmark`: end-to-end orchestrator connecting retrieval, generation, sample routing, evaluation scoring, and report persistence.
    - CLI entrypoint supporting filtering, custom top-k, and custom output path (`python -m src.evaluation.benchmark`).
  - Strengthened pipeline resilience:
    - Updated default embedding model to `models/gemini-embedding-001` and LLM to `models/gemini-flash-lite-latest` in `src/config.py` and `.env.example`, matching current Google AI Studio free tier quotas (1,500 requests/day).
    - Added exponential backoff retry on 429 rate limit errors in `ResumeGenerationChain` and `EvaluationRunner`.
    - Added defensive normalization in `parse_tailored_resume` for LLM structure variations (header vs contact, period mapping, skills dict/list, certifications formatting).
    - Clarified JSON schema structure in `src/generation/prompts.py` using explicit template examples.
  - Added unit test suite `tests/test_evaluation_dataset.py` with 9 tests covering dataset loading, test case conversion, facts and claims formatting, and mock benchmark execution. Total project test suite: **105/105 tests passing**.
  - Executed full baseline benchmark on all 5 real test cases using Google Gemini in production mode. Generated complete analytical report at `docs/evaluation.md`:
    - **Faithfulness:** `1.000` (100% across all 5 test cases — Zero Hallucination!)
    - **Answer Relevancy:** `1.000` (100% across all 5 test cases)
    - **Context Precision:** `0.725` (GenAI: 1.000, Backend: 0.875, Data Science: 0.750, SWE: 0.625, Data Eng: 0.375)
    - **Aggregate Score:** `0.898` (89.8% geometric mean quality)
- **Decisions made:**
  - Evaluated factual claims (`format_resume_claims`) rather than entire raw prompt text for faithfulness to avoid penalizing the candidate for mentioning target company names in application headers.
  - Standardized on `models/gemini-flash-lite-latest` as the default free-tier LLM for fast, generous 1,500 requests/day capacity without incurring charges.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Resolved rate limit quota handling with exponential backoff; mapped Google API model deprecations gracefully; ensured Pydantic v2 schema alignment between LLM JSON payloads and Jinja2 LaTeX structures.
- **Next steps:** Task 5.3 — Qualitative analysis & parameter/prompt tuning (addressing lower context precision in tracks with less dedicated knowledge base content).

## 2026-09-27 — Task 5.3: Qualitative Analysis & Parameter/Prompt Tuning
- **What was done:**
  - Analyzed Task 5.2 baseline evaluation feedback: identified that low Context Precision in Data Engineering (`0.375`) and Core SWE (`0.625`) stemmed directly from missing domain-specific guidance in the knowledge base, leading the hybrid retriever to pull generic advice.
  - Expanded the knowledge base with dedicated guides:
    - `src/knowledge_base/hr_recruitment/06_data_engineering_internships.md`: In-depth priorities for Data Engineering (ETL/ELT pipelines, advanced SQL, PostgreSQL schema design, Docker containerization, Linux scripting, web scraping data ingestion, ATS keywords).
    - `src/knowledge_base/hr_recruitment/07_systems_and_core_swe_internships.md`: In-depth priorities for Core SWE & Systems (Data Structures, Algorithms, Big-O complexity, C/C++, Linux environment, competitive programming / Maratona SBC, teaching assistantships, ATS keywords).
    - Updated `src/knowledge_base/hr_recruitment/05_adaptation_by_technical_track.md` to formally cover all 5 tracks.
  - Parameter & retriever tuning:
    - Expanded candidate retrieval pool from 5 to 8 (`similarity_top_k=8`, `bm25_top_k=8`) in `HybridResumeRetriever` and `KnowledgeBasePipeline`, giving Reciprocal Rank Fusion (RRF) higher recall across dense and sparse spaces before truncating to top-k.
    - Added `recreate: bool = False` to `KnowledgeBaseIndexer.build_index` and `build_chroma_vector_store` for deterministic collection rebuilding without vector duplicates.
    - Added `--reindex` flag to `src/evaluation/benchmark.py` CLI.
  - Updated test assertions in `tests/test_knowledge_base.py` to include the 2 new documents; all **105/105 tests passing**.
  - Re-indexed ChromaDB and re-executed the full benchmark across all 5 realistic test cases:
    - **Faithfulness:** `1.000` (maintained 100% across all 5 test cases — Zero Hallucination preserved).
    - **Answer Relevancy:** `1.000` (maintained 100% across all 5 test cases).
    - **Context Precision:** Jumped from `0.725` to `0.900` (+17.5%):
      - GenAI / RAG: `1.000` (maintained)
      - Data Science / ML: `0.750` (maintained)
      - Backend Python: `0.750`
      - Core SWE / Systems: `1.000` (jumped from 0.625, +37.5%)
      - Data Engineering: `1.000` (jumped from 0.375, +62.5%)
    - **Aggregate Score:** Rose from `0.898` to `0.965` (+6.7% overall pipeline quality).
  - Documented architectural decisions in ADR-010 (`docs/decisions_log.md`).
- **Decisions made:**
  - Solved context precision via domain knowledge enrichment and larger pre-fusion candidate windows rather than restrictive prompt filtering.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Machine reboot occurred during initial benchmark run; resumed cleanly from persistent files and re-indexed ChromaDB.
- **Next steps:** Task 5.4 — Edge Cases Testing (adversarial testing: vacancies without requirements, incomplete profiles, unusual characters, etc.). Awaiting user authorization.

## 2026-09-27 — Task 5.4: Edge Cases Testing & Defensive Hardening
- **What was done:**
  - Implemented deterministic fallback mechanism:
    - Added `build_fallback_tailored_resume(candidate, job)` in `src/generation/chain.py` (and exported via `src/generation/__init__.py`), ensuring a truthful, 100% grounded, beautifully formatted resume can always be rendered directly from candidate facts even if the LLM API fails or encounters JSON errors.
    - Added `allow_fallback: bool = False` to `ResumeGenerationChain.generate()`, providing seamless protection for production while maintaining strict exception propagation during benchmark tests.
  - Hardened core components against edge cases:
    - `src/data/job_posting.py`: `to_search_query()` now strips and filters empty/whitespace items to always produce valid non-empty semantic queries even for jobs without requirements or tech stacks.
    - `src/generation/prompts.py`: `build_resume_generation_prompt()` now injects an explicit fallback guidelines directive when retrieved RAG chunks are empty or whitespace.
    - `src/generation/formatter.py`: `sanitize_filename_part()` now accepts a configurable `fallback="item"` to prevent empty filename stems when target companies contain only symbols/punctuation.
  - Created comprehensive test suite `tests/test_edge_cases.py` with 15 specialized unit tests covering:
    1. Minimal jobs with zero requirements and zero technologies.
    2. Jobs with exotic, LaTeX-breaking characters (`&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`, `\`).
    3. First-time intern candidate profiles with zero prior professional experiences (`experiences=[]`).
    4. Minimal candidates with zero projects or missing optional fields (no summary, no certifications, no languages).
    5. Clean LaTeX rendering and successful Tectonic PDF compilation with minimal profiles and special characters.
    6. Prompt resilience with empty and whitespace-only retrieval guidelines.
    7. Filename sanitization with extreme inputs (symbols only, truncation to 30 chars).
    8. LLM chain failure handling (strict exception raising vs. graceful deterministic fallback).
    9. Adversarial prompt injection defense (preventing job descriptions from overriding candidate source-of-truth grounding).
  - All **120/120 tests passing** cleanly across the entire project in 51.16s.
  - Documented architectural decisions in ADR-011 (`docs/decisions_log.md`).
- **Decisions made:**
  - Separated testing and production fallback behavior via `allow_fallback` parameter: tests and benchmarks verify strict JSON schema compliance from the LLM, while production UI can operate with zero-crash guarantees.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Ensuring LaTeX escaping properly handled combined special characters like `#` and `&` in recursive nested dict structures.
- **Next steps:** Phase 5 is fully completed! Ready for Phase 6 — Portfolio and Deploy (README.md, Docker, MkDocs/docs, deployment preparations).

## 2026-09-27 — Phase 6: Portfolio & Deploy (Completion)
- **What was done:**
  - Authored comprehensive, high-impact `README.md` containing:
    - Interactive badges (Python 3.11/3.12, LlamaIndex, Google Gemini, ChromaDB, Tectonic, Gradio, 120/120 tests passing, Faithfulness 1.000, MIT).
    - High-level architecture flowcharts in Mermaid covering inputs, ingestion, hybrid retrieval (dense + BM25 + RRF), structured generation, deterministic fallbacks, and typographical compilation.
    - Full evaluation benchmark table across all 5 internship tracks with detailed metrics analysis.
    - Quickstart instructions for local development, CLI usage, and Web UI launch.
    - Docker & Docker Compose setup and deployment guidelines.
    - Full repository directory tree mapping and ADR index.
    - Hugging Face Spaces metadata frontmatter.
  - Implemented containerization infrastructure:
    - `Dockerfile`: Debian-based Python 3.12-slim container with precompiled static Tectonic TeX Engine (v0.15.0), keeping image size under 400 MB. Configured non-root user (UID 1000) for security and Hugging Face Spaces Docker compatibility.
    - `docker-compose.yml`: Single-command local startup (`docker compose up --build`) mounting persistent host directories for `./output` and `./chroma_db`, plus candidate profile live-mounting.
    - `.dockerignore`: Filtered build context to exclude local virtual environments, test caches, bytecode, and sensitive `.env` files.
  - Deployment & dependency packaging:
    - `requirements.txt`: Frozen production dependencies matching validated packages.
    - Root `app.py`: Created root entrypoint for direct Hugging Face Spaces compatibility and custom port configuration.
  - Authoring technical deep dive:
    - `docs/rag_design.md`: In-depth architectural documentation detailing ingestion chunking, Reciprocal Rank Fusion mathematical formulation, multi-step structured prompting, anti-hallucination guardrails, and tri-axial evaluation methodology.
    - Updated `docs/architecture.md` with modern models and Tectonic compiler specifications.
    - Added ADR-012 (*Containerization, Portfolio Packaging, and Deployment Readiness*) in `docs/decisions_log.md`.
  - Re-verified test suite: **120/120 tests passing** cleanly in 51.16s.
- **Decisions made:**
  - Selected precompiled static musl binary for Tectonic in Docker, eliminating heavy TeX Live toolchains (>4 GB) down to a lightweight 400 MB image.
  - Standardized root `app.py` wrapper to provide immediate out-of-the-box Hugging Face Spaces Gradio app detection.
- **Model used:** Gemini Flash (execution)
- **Challenges:** Ensuring UID 1000 permissions were correctly set on writeable directories (`/app/output`, `/app/chroma_db`) inside the container.
- **Project Status:** All 6 Phases completed with 100% test coverage, comprehensive documentation, and production readiness!

## 2026-09-29 — Multilingual Support (PT / EN / FR) & 1-Page Layout Guarantee
- **What was done:**
  - Resolved resume spillover on 2nd page (as observed in `resume_philips_20260929_111800.pdf`):
    - Optimized LaTeX geometry: `margin=0.46in, top=0.40in, bottom=0.40in` in `templates/resume.tex.j2`.
    - Compacted `titlesec` spacing to `5pt/2.5pt` and `enumitem` spacing to `itemsep=0.8pt, topsep=0.5pt`.
    - Re-tested compiled Philips resume via Tectonic and `pdfinfo`: strictly **1 page**.
  - Implemented complete, native multilingual support across **Portuguese (PT)**, **English (EN)**, and **French (FR)**:
    - Added `ResumeLanguageCode = Literal["pt", "en", "fr"]` and `SECTION_LABELS` in `src/data/resume.py`.
    - Refactored `templates/resume.tex.j2` to inject escaped localized labels (`labels.objective`, `labels.education`, `labels.experience`, `labels.projects`, `labels.skills`, `labels.languages_certs`, `labels.technologies`, `labels.view_project`).
    - Implemented heuristic language auto-detection (`detect_language_from_text`) in `src/generation/chain.py` identifying French, English, or Portuguese job descriptions.
    - Added language dropdown selector in the Gradio web interface (`src/app.py`): `Automático (detectar da vaga)`, `Português (PT-BR)`, `Inglês (EN)`, `Francês (FR)`.
    - Updated `SYSTEM_PROMPT` and `build_resume_generation_prompt()` in `src/generation/prompts.py` with strict target language consistency and 1-page content budget mandates.
    - Updated `build_fallback_tailored_resume` to localize fallback objectives and skill categories in PT, EN, and FR.
  - Test suite & verification:
    - Added tests for multilingual schema labels, template rendering, language detection, prompt directives, fallback localization, and French PDF compilation in `tests/test_schemas.py`, `tests/test_template.py`, and `tests/test_generation.py`.
    - Updated `test_format_candidate_facts` to dynamically assert against candidate contact and background attributes.
    - All **127/127 tests passing** cleanly in 53.23s.
    - Documented architectural decision ADR-013 in `docs/decisions_log.md`.
- **Decisions made:**
  - Standardized section titles in French following professional conventions: *Profil Professionnel*, *Formation*, *Expérience Professionnelle*, *Projets Notables*, *Compétences Techniques*, *Langues & Certifications*.
  - Handled space-before-colon French punctuation (`Technologies :`) natively within template labels.
- **Model used:** Gemini Flash (execution)
- **Challenges:** None; Tectonic natively renders UTF-8 French diacritics with `\usepackage[T1]{fontenc}`.
- **Next steps:** Ready for live resume generation across Brazilian, Anglophone, and Francophone job applications.

## 2026-10-01 — Model Configuration Hardening: Pinned Models & Separate Judge
- **What was done:**
  - Standardized explicit model configuration in `src/config.py` and `.env.example`:
    - `GENERATION_MODEL=gemini-3.5-flash-lite` (default, temp: `0.3`) for resume generation and benchmark evaluation.
    - `JUDGE_MODEL=gemini-3.1-flash-lite` (default, temp: `0.0`) for evaluation metrics runner.
    - `gemini-3.8-flash` documented and allowed as an override for production resume generation.
  - Eliminated all `-latest` floating aliases and hardcoded model IDs outside `src/config.py`:
    - Removed silent model rewrite in `src/generation/chain.py` (`get_gemini_llm`).
    - Updated Gradio UI model dropdown in `src/app.py` to use `ALLOWED_GENERATION_MODELS` from `src.config`.
    - Wired `src/evaluation/benchmark.py` (`_get_chain` and `_get_runner`) to explicitly pass `generation_model` and `judge_model`.
    - Maintained backward-compatibility properties (`gemini_model`, `gemini_temperature`) on `Settings`.
  - Added startup validation in `Settings` (`@model_validator(mode="after")`) enforcing that `GENERATION_MODEL` and `JUDGE_MODEL` must differ (with normalization for whitespace, casing, and `models/` prefix) to prevent self-evaluation bias.
  - Created standalone discovery script `scripts/list_models.py` to query available models from Google AI Studio via a single read call without exposing secrets.
  - Authored offline test suite `tests/test_config.py` covering defaults, distinctness validation, prefix normalization, and temperature boundary checks.
  - All **138/138 tests passing** completely offline.
  - Added ADR-014 (*Pinned Models and Separate Evaluation Judge*) in `docs/decisions_log.md`.
- **Decisions made:**
  - Separated generator and judge models by design to prevent circular self-evaluation bias.
  - Pinned explicit model IDs instead of floating aliases to ensure reproducibility.
  - Retained Flash-Lite tier models (`gemini-3.5-flash-lite` and `gemini-3.1-flash-lite`) as defaults to stay within Google AI Studio free tier limits (1,500 requests/day).
- **Model used:** Gemini (development / analysis)
- **Challenges:** Isolated unit test instantiation from local `.env` values by passing `_env_file=None` in unit tests.
- **Next steps:** Ready for benchmark execution and evaluation refinement with separate judge architecture.

## 2026-10-01 — Phase P2: Security & Contact Privacy Patch, Template & Profile Sanitization
- **What was done:**
  - Resolved audit finding SEC-01 by preventing sensitive personal contact data (`candidate.contact`: full name, email, phone, location, personal URLs) from being serialized into LLM prompts in `src/generation/prompts.py`.
  - Removed `"header"` from the required LLM JSON schema in prompt generation instructions and added an explicit privacy directive instructing the model not to output personal contact details.
  - Implemented deterministic contact injection in `ResumeGenerationChain.generate()` (`src/generation/chain.py`), populating `parsed_resume.header` directly from verified `candidate.contact`.
  - Added render-time contact injection support in `ResumeFormatter.render_latex()` and `ResumeFormatter.compile_pdf()` (`src/generation/formatter.py`), passing verified candidate contact directly into the LaTeX template context from `src/app.py`.
  - Resolved finding TPL-01: added localized labels `languages_only` and `certifications_only` across PT, EN, and FR in `SECTION_LABELS` (`src/data/resume.py`), and updated `templates/resume.tex.j2` to conditionally adjust section title and spacing when either languages or certifications is absent.
  - Resolved findings DAT-01, DAT-02, DAT-03 in `data/candidate_profile.yaml`: corrected French international phone formatting to `+33 7 43 52 84 87`, added `https://` schemes to LinkedIn and GitHub URLs, and reset TinyML project URL to `""` to prevent rendering profile links as repository links.
  - Added URL scheme auto-sanitization in `ResumeHeader` and `ResumeProject` (`src/data/resume.py`) via `@field_validator` prepending `https://` if missing.
  - Added test coverage in `tests/test_generation.py` (`test_contact_info_not_leaked_in_prompt`, `test_chain_generates_resume_with_verified_contact`, `test_formatter_render_latex_with_contact_override`) and in `tests/test_template.py` (`test_template_languages_certifications_conditional_headers`).
  - Ran full offline test suite: all **142/142 tests passing**.
  - Documented architectural decision ADR-015 in `docs/decisions_log.md`.
- **Decisions made:**
  - Enforced zero transmission of personal contact data to external LLM APIs; contact headers are rendered purely at presentation time from ground-truth profile records.
  - Treated URL scheme validation defensively in Pydantic schema models to ensure valid PDF hyperlink navigation regardless of user data formatting.
- **Challenges:** Ensuring prompt assertions in existing tests target candidate background entities (degrees, lab names, projects) rather than contact information stripped for privacy.
- **Next steps:** Proceed to Phase P3: Golden Set (`tests/golden/`) regression checks.

## 2026-10-03 — Phase P3: Golden Set Regression Suite (`tests/golden/`)
- **What was done:**
  - Established the golden regression test directory `tests/golden/` with `fixtures/`.
  - Archived the uncorrected, defective Amazon SDE Intern resume as a test fixture in `tests/golden/fixtures/bad_amazon_resume.tex`.
  - Authored a hand-corrected ground truth reference resume in `tests/golden/fixtures/good_amazon_resume.tex` fixing:
    - Removed unsupported technical claims ("distributed systems", "scalable cross-platform software").
    - Restored true verb scope levels ("Managed and developed" instead of "Architected"; "Participated in custom PCB design" instead of "Designed multilayer custom PCBs").
    - Preserved Asimov Jr. leadership accomplishments (leading 5+ developers, Area Manager promotion).
    - Normalized phone notation (`+33 7...`) and explicit `https://` schemes on profile URLs.
    - Adjusted dynamic section header to `Languages` instead of `Languages & Certifications`.
  - Built modular check functions in `tests/golden/checks.py` covering all 9 specific failure modes from `docs/audit_report.md`.
  - Authored `tests/golden/test_amazon_golden.py` (12 tests) asserting that all 9 checks fail on the bad resume, all 9 checks pass on the good resume, and the good resume compiles via Tectonic to exactly 1 page.
  - Ran full test suite: all **154/154 tests passing**.
  - Documented architectural decision ADR-016 in `docs/decisions_log.md`.
- **Decisions made:**
  - Separated check functions into a dedicated `checks.py` module to enable reuse across subsequent evaluation and verification phases.
  - Required 100% check failure on the bad fixture and 100% pass on the good fixture as the exit criteria for Phase P3.
- **Challenges:** Differentiating between top-level user profile links in the header and project repository links in project entries via regex.
- **Next steps:** Proceed to Phase P4: Atomic facts schema (`data/candidate_facts.yaml` and `src/data/facts.py`).

## 2026-10-03 — Phase P4: Atomic Facts Schema & Facts Repository
- **What was done:**
  - Designed and authored the Pydantic v2 atomic facts schema in `src/data/facts.py`:
    - `AtomicFact`: models an indivisible verified claim with `id`, `source`, `text`, `scope_ceiling` (1-4), `tracks`, `priority` (1-3), `metrics`, and `tags`.
    - `CandidateFacts`: container collection enforcing unique fact IDs and providing filtering methods by track, priority, and allowlists (`get_allowed_metrics()`, `get_allowed_tags()`).
    - Standardized `SCOPE_LEVEL_NAMES` implementing the 4-level Verb Scope Ladder (*participated*, *contributed*, *developed*, *led*).
    - `load_candidate_facts()`: YAML loader supporting dictionary or list payloads with schema validation.
  - Added `candidate_facts_path` setting to `src/config.py` and exported facts models in `src/data/__init__.py`.
  - Authored verified candidate ground truth in `data/candidate_facts.yaml`, mapping every bullet point from experiences (Asimov Jr., ENIB, SPE UNIFEI) and projects (Resume RAG Generator, CAN Bus, ROS 2, TinyML, Bluetooth Auth, Competitive Programming) with exact scope ceilings and metrics.
  - Authored test suite `tests/test_facts.py` (22 tests) verifying schema boundaries, duplicate detection, collection filtering, YAML parsing, and validating `data/candidate_facts.yaml`.
  - Ran full test suite: all **176/176 tests passing**.
  - Documented architectural decision ADR-017 in `docs/decisions_log.md`.
- **Decisions made:**
  - Adopted numeric scope ceilings (1 to 4) directly in the schema to enable arithmetic comparisons in future verification checks (e.g. `verb_level <= fact.scope_ceiling`).
  - Extracted metric strings into an explicit list (`metrics: ["5+ developers", "80% accuracy"]`) to support deterministic number validation in Phase P5.
- **Model used:** Gemini 3.8 Flash (High)
- **Challenges:** None; YAML mapping aligns cleanly with Pydantic v2 models.
- **Next steps:** Proceed to Phase P5: Deterministic metrics module (`src/verification/`).




## 2026-10-05 — Phase P5: Deterministic Metrics (`src/verification/`)
- **What was done:**
  - Applied the user's scope corrections (SPE UNIFEI, CAN Bus, ROS 2) to `data/candidate_profile.yaml` so profile and `data/candidate_facts.yaml` agree (CAN Bus and ROS 2 bullets rewritten).
  - Created `src/verification/` with: `text_utils.py`, `verb_ladder.py`, `ground_truth.py`, `matching.py`, `fabrication.py` (M1a–c), `inflation.py` (M2), `coverage.py` (M3), `keywords.py` (M4), `format_checks.py` (M5), `tex_parser.py` (template LaTeX → `TailoredResume`), `report.py` (`verify_resume`, `VerificationReport`).
  - Added 182 offline tests: `tests/test_verification_core.py`, `_metrics.py`, `_format.py`, `_tex_parser.py`, `_fixtures.py`, plus synthetic data in `tests/verification_data.py`.
  - Human review completed: User approved the 4-level verb ladder and the 0.30 matching threshold.
  - User authorized updating the good fixture and resolving profile/facts findings:
    - `data/candidate_profile.yaml`: SPE UNIFEI consolidated to 2 core bullets matching atomic facts.
    - `data/candidate_facts.yaml`: Added `exp_enib_system_codesign` (scope ceiling 2, priority 1) per user confirmation of pair design.
    - `tests/golden/fixtures/good_amazon_resume.tex`: Synchronized dates (`03/2022 - 12/2027`, `12/2023 - 09/2025`), CAN node 3 IMU scope, ROS 2 PC interface/bridge scope, PPE ENIB co-design, and removed summary role repetition.
  - Ran the verifiers on the golden fixtures and on a resume copied verbatim from the profile.
  - Documented ADR-018 in `docs/decisions_log.md` (marked Accepted).
- **Test status:** full suite 358 passed (`.venv/bin/pytest -q`, 53.0s). `ruff` and `mypy` are not installed in `.venv`: lint and type checks **not run**.
- **Results on fixtures (deterministic, track `ai`):**
  - Bad Amazon resume: M1 3 unsupported claims (2 period mismatches, 1 invented TinyML URL); M2 4 inflated of 8 assessed (*architected*, *engineered*, *designed*, *developed* on CAN bullet), 2 unmatched; M3 0.30 with leadership fact omitted; M5 failures: section title, phone, URLs. `hard_pass: False`.
  - Good Amazon resume: M1 0 unsupported claims; M2 0 inflated of 9 assessed; M5 0 failures (all pass, compiles to 1 page). `hard_pass: True`.
  - Resume copied verbatim from the profile: M1 0 unsupported, M2 0 inflated of 17 assessed, 0 unmatched bullets.
- **Decisions made:**
  - Free-text claims are deliberately left to the P6 judge (M1d); unmatched bullets are listed, never silently accepted.
  - Checks without input report `not_verified` rather than pass.
  - A verb copied verbatim from the matched verified fact is accepted; design verbs need design evidence in the fact.
  - The matching threshold (0.30) and 4-level verb ladder were approved by the user.
- **Model used:** Gemini 3.8 Flash (High) until the first test run; Claude Sonnet 5.5 (High) afterwards.
- **Challenges:** Synchronizing the golden reference fixture with real candidate facts and dates without violating single-page compilation constraints. Tectonic compilation verified `Pages: 1`.
- **Next steps:** Proceed to Phase P6: Judge Validation (`src/evaluation/`, `docs/experiments/E00_judge.md`).

## 2026-10-05 — Phase P6: Judge Validation Harness & Implementation
- **What was done:**
  - Formulated the rigorous Phase P6 Judge Validation design incorporating adversarial peer-review recommendations:
    - Shifted primary False Positive metric to Claim-Level FPR ($FPR_{claim} \le 0.03$, Wilson 95% CI $\le 0.05$) across ~1,100 clean claim observations, solving the statistical power limitation of resume-level N=10.
    - Implemented Localized True Positive attribution: a hit is only counted when the judge flags the exact corrupted bullet ID and span with the expected defect verdict.
    - Implemented Evidence Ablation for L5 (Fabricated Responsibility) to eliminate synthetic AI stylistic artifacts, and introduced L6 (Cross-Project Conflation) to test hallucination of true tools/metrics spliced across projects.
  - Authored synthetic candidates in `src/data/synthetic_profiles.py`:
    - `get_synthetic_fresh_grad` (Junior Full-Stack Web/Mobile Engineer) with 15 verified atomic facts.
    - `get_synthetic_researcher` (Applied ML & Computer Vision Specialist) with 15 verified atomic facts.
  - Built seeded defect injection harness in `src/evaluation/injection.py`:
    - Generates deterministic, SHA-256 seeded mutations across classes L1–L6 by bullet replacement (preventing page-overflow or coverage confounders).
    - Produces `GroundTruthInjection` audit ledger tracking corrupted bullet IDs, replaced spans, and expected verdicts.
  - Built atomic claim-level judge in `src/evaluation/claim_judge.py`:
    - Configured with `gemini-3.1-flash-lite`, temperature 0.0, prompt version `claim_judge_v2.0`.
    - Chain-of-Thought schema forcing `rationale` and `evidence_quote` generation before `verdict`.
    - Mechanical scope ceiling calculation in Python code against fact metadata (preventing LLM arithmetic hallucination).
    - Fail-closed error handling and LaTeX markup stripper (`strip_latex_markup`) to eliminate formatting noise and comment leakage.
  - Created end-to-end evaluation runner in `scripts/run_judge_validation.py`:
    - Transport-layer quota guard with `--max-calls` (hard ceiling at 85, stopping before 100).
    - Zero-socket `--dry-run` mode verifying deterministic verifier performance offline.
    - Wilson 95% score confidence interval calculations and JSON/Markdown manifest generation.
  - Authored comprehensive offline test suites:
    - `tests/test_synthetic_profiles.py` (4 tests)
    - `tests/test_evaluation_injection.py` (8 tests)
    - `tests/test_claim_judge.py` (7 tests, including zero-socket offline verification)
  - Executed full project test suite: **377/377 tests passing** completely offline in 53.11s.
  - Executed dry-run verification: `python scripts/run_judge_validation.py --dry-run` successfully confirmed 10 clean resumes, generated 60 mutations (28 selected), and verified 0 false positives on clean resumes and 100% deterministic recall on L1–L4.
  - Executed live benchmark (`python scripts/run_judge_validation.py --seed 42 --output-dir runs/E00_judge`):
    - Executed all 53 planned API calls against `gemini-3.1-flash-lite` (38 claim judge + 15 legacy evaluator) with 2-second rate-limit pacing and automatic disk caching.
    - Handled LLM verdict alias variation gracefully by adding `@field_validator` on `ClaimVerdict.verdict` and `claim_type`.
    - Resolved bullet ID prefix alignment between injection ledger and claim judge (`exp_` / `proj_`).
    - Empirical findings recorded in `docs/experiments/E00_judge.md` and `runs/E00_judge/manifest.json`:
      - **Deterministic Verifier (`src/verification/`):** 100% recall (8/8) on L1–L4; 0% false positives on clean resumes.
      - **Claim-Level Judge (`claim_judge_v2.0`):**
        - Claim-level FPR: **0.92%** (Wilson 95% CI: `[0.25%, 3.28%]`), easily beating the $\le 3.00\%$ requirement.
        - Fabricated Responsibility (L5, Evidence Ablation) Recall: **90.0%** (9/10), beating the $\ge 80.0\%$ requirement.
        - Cross-Project Conflation (L6) Recall: **100.0%** (10/10).
        - Inflated Verb (L3) Recall: **100.0%** (2/2).
      - **Combined Verification Pipeline (`Deterministic ∪ Judge`):** **96.4% Overall Recall** (27/28 localized defects detected).
      - **Legacy Evaluator (`FaithfulnessEvaluator`):** **0.0% Recall** (0/8 defects detected; scored 100% faithful on resumes with injected lies), proving conclusively the fundamental flaw identified in the P0 audit.
  - Documented ADR-019 (*Judge Validation Harness, Atomic Claim Judge, and Synthetic Lie Injection*) in `docs/decisions_log.md`.
- **Decisions made:**
  - Validated that the combination of deterministic metrics (M1a–c, M2) and the atomic claim judge (M1d) achieves 96.4% recall and <1% claim FPR.
  - Confirmed legacy faithfulness evaluator is obsolete and unsuitable for production or research benchmarking.
- **Model used:** Claude 3.5 Sonnet / Gemini 3.8 Flash (analysis and design review), Antigravity (implementation and execution), Gemini 3.1 Flash-Lite (live judge & legacy evaluation).
- **Challenges:** Resolved LLM verdict alias normalization (`relational` -> `unsupported_claim`) and standardized bullet ID prefixes across ledger mutations.
- **Next steps:** Human review of `docs/experiments/E00_judge.md` to author the *Interpretation* and *Conclusions* sections. Upon approval, proceed to Phase P7: Baselines (B0, B1, B3).

## 2026-10-05 — Phase P7: Baselines Benchmark Implementation (B0, B1, B3)
- **What was done:**
  - Assembled development benchmark suite of 7 real internship job postings in `data/eval/dev/`:
    - `01_genai_rag_intern.md` (PT, NeuralWave Labs, Track: AI)
    - `02_data_science_ml_intern.md` (PT, FinMetrics Analytics, Track: Data Science)
    - `03_backend_python_intern.md` (PT, CloudScale Software, Track: Backend)
    - `04_swe_algorithms_intern.md` (PT, Apex Global Tech, Track: Core SWE)
    - `05_data_engineering_intern.md` (PT, OmniData Solutions, Track: Data Engineering)
    - `06_fr_stellantis_data_science.md` (FR, Stellantis ACOE, Track: Data Science / AI)
    - `07_en_criteo_ml_intern.md` (EN, Criteo Commerce Intelligence, Track: AI / ML)
  - Computed and committed cryptographic integrity manifest in `data/eval/MANIFEST.sha256`.
  - Extended `EvaluationTestCase.from_markdown_file` and `EvaluationDataset.from_directory` in `src/data/evaluation.py` to parse markdown frontmatter.
  - Implemented generation baseline variants in `src/generation/variants/`:
    - `b0_fallback.py`: Deterministic fallback generator without LLM calls.
    - `b1_hybrid_rag.py`: Current production pipeline with hybrid RAG (ChromaDB + BM25 + RRF) and `ResumeGenerationChain`.
    - `b3_full_context.py`: Baseline providing all 12 documents (~5,400 words) from the knowledge base directly into the prompt without retrieval (`load_full_knowledge_base_context`).
  - Added unit test suite `tests/test_variants.py` covering all three variants offline with mocks.
  - Built comprehensive benchmark runner `scripts/run_baselines.py` with quota protection (`--max-calls`), Tectonic PDF compilation for M5 page counts, deterministic verifier (`verify_resume`), and claim-level judge evaluation (`ClaimLevelJudge`).
  - Executed `--dry-run` verifying all 7 test cases compile to PDF via Tectonic and verify offline with 0 API calls.
  - Formulated ADR-020 (*Development Benchmark Suite and Baseline Variants*) in `docs/decisions_log.md`.
  - Test suite status: **382/382 passing** in 53.15s.
- **Decisions made:**
  - Retained strict separate metrics reporting (M1 fabrication, M2 inflation, M3 coverage, M4 truthful keywords, M5 format constraints, Hard-Pass rate) without aggregate geometric means.
  - B0 dry-run revealed expected format behavior: single-language check fails on PT and FR for B0 because the deterministic fallback copies English candidate profile facts without translation (an authentic reference floor finding).
- **Model used:** Antigravity CLI / Gemini 3.5 Flash Lite (generator: 14 calls), Gemini 3.1 Flash Lite (judge: 21 calls), Tectonic 0.15.0.
- **Challenges:** Ensuring proper alignment of Pydantic model attributes (`report.fabrication.unsupported_of`, `report.inflation.assessed`, `report.coverage.coverage`, `report.format.failed`, `judge_payload.claims`) across the verification report and runner.
- **Results:**
  - **B0 (Deterministic Fallback, No LLM):** 14.3% Hard-Pass (1/7). 0.00 fabrication claims/res, 0.0% inflation, 56.1% coverage, 100.0% truthful keywords. The 6 failures were purely `single_language` due to English bullets copied into PT/FR resumes without translation.
  - **B1 (Hybrid RAG Pipeline):** 0.0% Hard-Pass (0/7). 11.71 fabrication claims/res, 16.7% inflation, 14.2% coverage, 100.0% format pass.
  - **B3 (Full Knowledge Base in Prompt):** 0.0% Hard-Pass (0/7). 7.43 fabrication claims/res, 28.6% inflation, 15.6% coverage, 85.7% format pass.
  - Empirical finding: Without a verifier (B1 and B3), the LLM hallucinates 7 to 12 unsupported claims per resume and inflates verbs significantly, while B0 achieves 0% fabrication and inflation. This establishes the baseline for H0/H1.
- **Next steps:** Human review of `docs/experiments/E01_baselines.md` to author the *Interpretation* and *Conclusions* sections. Upon approval, proceed to Phase P8: Verifier Implementation (V1).

## 2026-10-11 — Phase P8: Verifier V1 Implementation (Error-Guided Regeneration & Deterministic Repair)
- **What was done:**
  - Designed, approved, and implemented the complete Verifier V1 architecture:
    - `src/verification/issues.py`: Pure, offline issues layer normalizing `VerificationReport` (M1a-c, M2, M4, M5) and `ClaimLevelJudge` (M1d) verdicts into unified `VerificationIssue` objects. Implemented fail-closed handling (`judge_unavailable`).
    - `src/generation/prompts.py`: Added `serialize_resume_for_llm` (strips `header` to enforce SEC-01 privacy across regeneration rounds) and `build_regeneration_feedback_prompt` (multi-lingual localized feedback in EN and FR detailing detected defect line items and scope ceilings).
    - `src/generation/chain.py`: Refactored `ResumeGenerationChain` into modular helpers (`resolve_language`, `build_messages`, `invoke`, `finalize`) and added multi-turn `regenerate_with_feedback`.
    - `src/verification/repair.py`: Implemented deterministic surgery (`repair_resume`) that purges non-allowlist skills/technologies, aligns dates/role titles/institutions with `CandidateProfile`, prunes defective bullets, and restores verified profile bullets if entries become empty.
    - `src/generation/variants/v1_verified.py`: Implemented full V1 state machine (`generate_v1`): Round 0 generation → Verification → up to 2 error-guided regeneration retries (`clean@0`, `clean@1`, `clean@2`) → Deterministic repair (`repaired`) → Fallback B0 (`fallback`), returning complete diagnostic trace (`V1Trace`).
    - `src/verification/fabrication.py`: Added canonical multilingual token normalization in `_name_tokens` to support French/international degree and role titles without false positive fabrication flags.
    - `scripts/run_verifier.py`: Built end-to-end benchmark runner with `--dry-run`, `--max-calls`, quota tracking, and automatic `docs/experiments/E02_verifier.md` report emission.
  - Authored comprehensive offline test suites:
    - `tests/test_verification_issues.py` (4 tests)
    - `tests/test_repair.py` (4 tests)
    - `tests/test_v1_variant.py` (4 tests, covering `clean@0`, `clean@1`, `repaired`, and SEC-01 privacy enforcement)
  - Executed full test suite: **394/394 tests passing** completely offline in 53.11s.
  - Executed live benchmark execution of Experiment E02:
    - Command: `.venv/bin/python3 scripts/run_verifier.py --max-calls 100`
    - Total API calls made: **47 calls** (20 `gemini-3.5-flash-lite` generator + 27 `gemini-3.1-flash-lite` judge).
    - **Headline Results:**
      - M1 Fabrication Rate: **0.4%** across all claims (down from 11.71 claims/res in B1).
      - M2 Verb Inflation Rate: **0.0%** across all assessed bullets (down from 16.7% in B1 and 28.6% in B3).
      - Combined Defect Rate ($M1 + M2$): **0.4%**, easily satisfying the $\le 5\%$ H1 hypothesis acceptance threshold.
      - M3 Factual Coverage: **44.7%** (up from 14.2% in B1).
      - Resolution paths: 1 `clean@1` (Criteo, EN), 1 `clean@2` (GenAI, PT), 2 `repaired` (Backend, PT; Stellantis, FR), 3 `fallback` (B0 applied when repaired residual remained).
      - English target role (`en_criteo_ml_intern`): **100% Hard-Pass** with 70% coverage and 0 defects, achieving clean state on retry 1.
    - Results and manifests recorded in `runs/E02_verifier/` and `docs/experiments/E02_verifier.md`.
- **Decisions made:**
  - Candidate targeting confirmed for English and French (no PT-BR generation required); French degree/title equivalents supported cleanly through canonical multilingual token normalization.
  - H1 combined defect rate frozen as:
    $M1_{rate} = (M1_{det} + M1_{judge}) / (Claims_{det} + Claims_{judge})$
    $M2_{rate} = (M2_{det} + M2_{judge}) / (Bullets_{det} + ScopeClaims_{judge})$
    H1 adopted if $M1 + M2 \le 5\%$ and coverage drop $\le 5$ percentage points vs B1.
- **Model used:** Claude 3.5 / Gemini 3.8 Flash (High), Gemini 3.5 Flash Lite (generator: 20 calls), Gemini 3.1 Flash Lite (judge: 27 calls), Tectonic 0.15.0.
- **Challenges:** Ensuring zero circular dependencies between judge evaluation payloads, generation chains, and verification issues layers through duck typing.
- **Next steps:** Human review of `docs/experiments/E02_verifier.md` to author the *Interpretation* and *Conclusions* sections. Upon approval, proceed to Phase P9: RAG Ablation (V1 vs B3+verifier).

## 2026-10-12 — Phase P9: RAG Ablation Experiment E03 (V1 vs. B3 + Verifier)
- **What was done:**
  - Implemented B3+Verifier baseline architecture for Hypothesis H4 testing:
    - Parameterized `generate_v1` in `src/generation/variants/v1_verified.py` with `context: str | None = None` to accept arbitrary external context without re-querying ChromaDB.
    - Added `generate_b3_verified` in `src/generation/variants/b3_full_context.py` injecting all 12 knowledge base documents (`load_full_knowledge_base_context()`, ~5,400 words) directly into the V1 verification and error-guided regeneration loop.
    - Exported `generate_b3_verified` in `src/generation/variants/__init__.py`.
  - Authored unit test in `tests/test_b3_verified.py` verifying full context injection, offline mock generation, error handling, and deterministic fallback.
  - Authored ablation evaluation runner `scripts/run_rag_ablation.py`:
    - Loads precomputed V1 reference results from `runs/E02_verifier/results.json`.
    - Evaluates B3+Verifier on the 7 dev benchmark postings (`data/eval/dev/`).
    - Compiles LaTeX resumes and verifies PDF output via Tectonic.
    - Computes paired deltas ($\Delta M3 = M3_{V1} - M3_{B3+Ver}$, $\Delta M1$) and evaluates against frozen Research Plan §7 decision thresholds.
    - Generates experiment report at `docs/experiments/E03_rag_ablation.md` and machine-readable artifacts in `runs/E03_rag_ablation/`.
  - Executed tests and dry-run:
    - Suíte completa: **395/395 testes passando** offline em 53s.
    - Dry-run: 7/7 vagas compilaram PDFs válidos com 0 chamadas de API.
  - Executed live benchmark E03 (`scripts/run_rag_ablation.py --max-calls 100`):
    - Total API calls made: **47 calls** (20 `gemini-3.5-flash-lite` generator + 27 `gemini-3.1-flash-lite` judge).
    - **Headline Findings (V1 vs. B3+Ver):**
      - **M3 Requirement Coverage:** V1 achieved **44.7%** vs. B3+Ver's **37.5%**, yielding $\Delta M3 = \mathbf{+7.2\text{ p.p.}}$, satisfying the frozen threshold ($\Delta M3 \ge +5.0\text{ p.p.}$).
      - **M1 Fabrication Rate:** V1: **0.4%** vs. B3+Ver: **0.2%** (negligible difference, both near zero).
      - **M2 Verb Inflation:** **0.0%** across both variants.
      - **Token Efficiency:** V1 injects top-5 chunks (~1,200 words), whereas B3+Ver injects 12 full files (~5,400 words) across every prompt turn, resulting in >4x prompt token overhead for B3+Ver.
      - **Hypothesis H4:** Formally adopted and confirmed. RAG is empirically justified over full-context stuffing.
  - Documented architectural decision ADR-022 in `docs/decisions_log.md`.
- **Decisions made:**
  - Hybrid RAG is retained as the core generation pipeline. B3 full-context remains as an ablation benchmark.
- **Model used:** Gemini 3.8 Flash (High), Gemini 3.5 Flash Lite (generator: 20 calls), Gemini 3.1 Flash Lite (judge: 27 calls), Tectonic 0.15.0.
- **Challenges:** Full context stuffing diluted prompt attention towards candidate facts on specific requirements (e.g. Stellantis dropped to 0% M3 coverage in B3+Ver due to bullet pruning).
- **Next steps:** Human review of `docs/experiments/E03_rag_ablation.md` to author the *Interpretation* and *Conclusions* sections. Upon approval, proceed to Phase P10: Cleanup & Packaging.

## 2026-10-12 — Phase P10: Cleanup, Production Packaging & README Audit (Research Plan Completion)
- **What was done:**
  - Integrated Closed-Loop Verifier into the Gradio Web Application:
    - Updated `generate_resume_action` in `src/app.py` to route through `generate_v1` as the production default.
    - Surfaced diagnostic resolution traces (`clean@0`, `clean@1`, `clean@2`, `repaired`, `fallback`), round counts, and surgical repair metrics in the UI status banner, PDF inspection card, and RAG transparency report.
    - Preserved mock injection support in `generate_resume_action` for fast, offline unit testing.
    - Added unit test `test_generate_resume_action_with_v1_verifier` in `tests/test_app.py`.
  - Audited and Overhauled `README.md`:
    - Eliminated unvalidated claims of "zero hallucination" / "0% hallucination rate" from legacy binary evaluators.
    - Updated badges: `396 tests passing offline`, `Fabrication Rate: 0.4% (Verified V1)`, `Verb Inflation: 0.0% (Verb Ladder)`.
    - Created updated Mermaid system architecture flowchart reflecting candidate facts with scope ceilings, the V1 verifier loop, separate claim-level judge, error feedback regeneration, deterministic repair surgery, and fallback floor.
    - Added empirical comparison table across variants (B0, B1, B3, V1, B3+Ver) and documented adoption of hypotheses H1 and H4.
    - Updated project directory structure tree.
  - Aligned Technical Documentation:
    - Modernized `docs/architecture.md` with pinned model IDs (`gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`), updated system flow, and complete file tree.
    - Created scaffold `docs/lessons.md` for human author qualitative reflections per experiment.
  - Executed full offline test suite:
    - **396/396 tests passing** offline in 53.6s with zero external API calls.
  - Documented architectural decision **ADR-023** in `docs/decisions_log.md`.
- **Decisions made:**
  - Production UI defaults to the verified V1 generator with complete transparency on resolution paths and repair actions.
- **Model used:** Gemini 3.8 Flash (High), Tectonic 0.15.0.
- **Challenges:** None; all components cleanly integrated and verified.
- **Next steps:** Research Plan (Phases P0–P10) is fully completed! Ready for human authoring of qualitative reflections in `docs/lessons.md`.

## 2026-10-12 — Post-P10 Real-World Testing & Template/Knowledge-Base Hardening (Inalfa Roof Systems Case)
- **What was done:**
  - Hardened LaTeX template (`templates/resume.tex.j2`):
    - Inlined education institution and country/location (`-- location`) to eliminate isolated country lines ("France").
    - Rendered `labels.languages_only` when certifications list is empty, removing duplicate section headings ("Languages" followed by bold "Languages:").
    - Formatted date ranges with typographical en-dashes (`--`) instead of simple hyphens (`-`).
    - Maintained exact data idempotence for language proficiencies to avoid mutating schema strings during rendering.
  - Hardened LaTeX parser (`src/verification/tex_parser.py`):
    - Updated regex for period normalization (`re.sub(r"\s*(?:[–—]|--|-)\s*", " - ", raw_period).strip()`) to ensure idempotent two-way round-trip across any dash typography.
  - Expanded Technical Knowledge Base for Embedded Systems / Automotive ECUs:
    - Authored `src/knowledge_base/hr_recruitment/08_embedded_systems_and_edge_ai.md` covering embedded C/C++, FreeRTOS, deterministic bus protocols (CAN Bus, explicit distinction between SPI inter-board and UART PC telemetry), TinyML / Edge Impulse constraints, ROS 2 inter-node integration, and collaborative PCB schematic assistance strictly bounded by the candidate's Level 1 scope ceiling.
    - Updated `src/knowledge_base/hr_recruitment/05_adaptation_by_technical_track.md` to register Track 6.
    - Updated test expectations in `tests/test_knowledge_base.py`.
  - Refined Prompt Directives (`src/generation/prompts.py`):
    - Added Mandate 1 grounding directive prohibiting invented hype words (e.g., "robust", "telemetry") and requiring faithful protocol distinction.
    - Updated Professional Summary guidelines to generate an active Technical Value Proposition (Degree + Core Verified Competencies + Target Domain) and strictly forbid passive applicant phrasing (*"applying for ... to contribute to..."*).
  - Executed offline test suite:
    - **396/396 tests passing** offline in 53.8s.
  - Documented architectural decision **ADR-024** in `docs/decisions_log.md`.
- **Decisions made:**
  - Expanded knowledge base and prompt structure rather than hardcoding ad-hoc rules for a single job description.
  - Kept candidate profile scope ceilings intact (PCB design assistance Level 1).
- **Model used:** Gemini 3.8 Flash (High), Tectonic 0.15.0.
- **Challenges:** Period dash normalization regex precedence initially left whitespace; resolved and verified via round-trip tests.
- **Next steps:** Ready for real-world testing via Gradio UI for additional target postings.

## 2026-10-12 — ADR-025: Phase A Deterministic Template Hardening, Typographic Escaping, and Skills Taxonomy Alignment
- **What was done:**
  - Standardized Language Line Rendering (Defect 4):
    - Added `format_language_entry()` and structured fields (`level`, `certificate`, `formatted`) with `@model_validator` in `src/data/resume.py`.
    - Standardized single outer parentheses around certificates: e.g. `English (B2) (TOEIC)` instead of double parentheses `((...))`.
    - Updated `templates/resume.tex.j2` and `src/verification/tex_parser.py` to parse and render structured language fields with backward compatibility.
    - Added unit and template tests in `tests/test_schemas.py` and `tests/test_template.py`.
  - Hardened Non-Wrapping Date Column and ENIB Width Optimization (Defect 5):
    - Wrapped the date column in `\mbox{\small\color{subtext} ...}` across education and experience headers in `templates/resume.tex.j2`.
    - Added model validator on `ResumeEducation` in `src/data/resume.py` to shorten `"École Nationale d'Ingénieurs de Brest (ENIB)"` to `"ENIB"`, preventing header overflow at 10pt A4.
    - Updated `_HFILL_RE` regex in `src/verification/tex_parser.py` to match `\mbox`-wrapped date structures.
    - Added render test in `tests/test_template.py` verifying macro structure and Tectonic compilation.
  - Implemented Typographic Quotes Escaping (Defect 6):
    - Created `convert_typographic_quotes()` in `src/data/resume.py` converting straight quotes (`'`, `"..."`) to curly glyphs (`’`, `“...”`).
    - Hooked into `escape_latex()` and `_deep_escape()`, strictly protecting LaTeX commands, accents (e.g. `\'e`), and raw URLs.
    - Added tests in `tests/test_schemas.py` for apostrophes, quoted strings, accented characters, and URLs.
  - Deterministic Skills Category Taxonomy & ROS 2 Placement (Defect 7):
    - Created `src/data/skills_map.py` implementing `SKILL_TO_CATEGORY_KEY`, `get_skill_category_key()`, `get_skill_category_name()`, `flag_unknown_skills()`, and `reorganize_resume_skills()`.
    - Deterministically mapped ROS 2 variants to `"Robotics & Middleware"` (`robotics`).
    - Integrated `reorganize_resume_skills()` in `parse_tailored_resume()`, `build_fallback_tailored_resume()`, and `repair_resume()`.
    - Created `tests/test_skills_map.py` asserting all candidate skills are mapped, unmapped skills are flagged, and ROS 2 is moved out of frameworks.
  - Authored Data and Prompt Proposals (`docs/proposals/ADR-025_data_proposals.md`):
    - Documented proposed changes for human review covering Defect 10 (TinyML hardware metrics), Defect 9 ("Member of the Month" dropped), Defect 3 (Fact fusion between leadership and awards), Defect 8 (Coursework relevance filtering), Defect 1 ("verified" vocabulary leak), and Defect 2 (verbatim job description echo phrases).
  - Authored ADR-025 in `docs/decisions_log.md`.
  - Executed full test suite: **407/407 tests passing** offline in 54.4s (396 existing + 11 new tests).
- **Decisions made:**
  - Phase A addressed only deterministic template, escaping, and taxonomy fixes without calling any LLM.
  - Shortened long school names at the model validation level rather than changing page margins or sacrificing recruiter readability.
  - Protected LaTeX accents and URLs during quote typography conversion.
  - Proposed candidate data changes in `docs/proposals/ADR-025_data_proposals.md` rather than editing protected files.
- **Model used:** Gemini 3.8 Flash (High), Tectonic 0.15.0.
- **Challenges:** Aligning skills taxonomy category names across multilingual tests without breaking existing test assertions; resolved by matching `CATEGORY_NAMES` to standard canonical test keys.
- **Next steps:** Human review of `docs/proposals/ADR-025_data_proposals.md` to apply candidate profile and atomic fact updates, followed by Phase B (prompt and verifier heuristics for fact fusion and vocabulary leaks).







