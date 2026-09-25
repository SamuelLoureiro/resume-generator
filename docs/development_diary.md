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
- **Next steps:** Refactoring Phase 2 — Refactor data ingestion, chunking, vector store, retrieval, and generation modules.
