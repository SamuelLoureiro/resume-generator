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

## Phase 2: Core Pipeline Refactoring
- [ ] Refactor data ingestion, chunking, and vector store modules.
- [ ] Refactor retrieval and generation modules.
- [ ] Update utility scripts, configurations, and environment variable names if needed.

## Phase 3: Verification
- [ ] Validate cross-module imports.
- [ ] Run test scripts / ingestion pipeline to verify end-to-end functionality.