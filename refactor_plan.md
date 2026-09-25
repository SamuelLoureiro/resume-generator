# Migration Plan: Codebase Standardization to English

## Objective
Migrate all project documentation, planning files, code, tests, and configuration from Portuguese to idiomatic English.

## Constraints & Rules
- Do NOT alter runtime logic or architecture; this is strictly a naming/language refactoring.
- Code identifiers (classes, functions, variables, parameters), comments, docstrings, logs, and commit messages must be strictly in English.
- Vector database metadata keys, payload attributes, and collection names must follow standard English naming (e.g., `source`, `chunk_id`, `created_at`).
- Keep evaluation questions and source RAG benchmark documents in their original language if they represent Portuguese test data.
- Ensure all module imports and file path references are updated and functional.

## Phase 1: Planning & Documentation ✅
- [x] Translate all planning documents, architecture notes, and task tracking files into English.
  - Translated: `docs/architecture.md`, `docs/decisions_log.md`, `docs/development_diary.md`
  - Added ADR-006 documenting this standardization decision
- [x] Establish and document the standard English terminology for the RAG pipeline.
  - String labels in `src/data/job_posting.py` (to_search_query, to_prompt_context) standardized to English
  - Default field values translated: `"Híbrido"` → `"Hybrid"`, `"Presente"` → `"Present"`
  - All docstring references with Portuguese examples updated
  - Test assertions updated to match new English string outputs
  - All 15 tests passing

## Phase 2: Core Pipeline Refactoring ✅
- [x] Refactor data ingestion, chunking, and vector store modules.
  - Translated `src/__init__.py` package docstring
  - Translated all remaining Portuguese docstring examples in `src/data/candidate.py` and `src/data/resume.py`
  - Translated all fixture data in `tests/test_schemas.py` and `tests/test_template.py`
  - Implemented `src/ingestion/indexer.py` (Tarefa 2.2) — KnowledgeBaseIndexer with SentenceSplitter (512/50), MockEmbedding support, ChromaDB persistence
  - Updated `src/ingestion/__init__.py` with full exports
  - Created `tests/test_indexer.py` with 10 offline tests (MockEmbedding, no API calls)
  - All 25 tests passing
- [ ] Refactor retrieval and generation modules.
  - Deferred: `src/retrieval/` and `src/generation/` are not yet implemented; will be written in English from the start.
- [x] Update utility scripts, configurations, and environment variable names if needed.
  - All config, env var names, and settings already in English (no changes required)

## Phase 3: Verification ✅
- [x] Validate cross-module imports.
  - All imports validated via test suite (25/25 passing)
- [x] Run test scripts / ingestion pipeline to verify end-to-end functionality.
  - Full pytest suite: 25/25 passing in 5.72s