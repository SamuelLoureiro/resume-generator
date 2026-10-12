# Resume Generator RAG — Project Rules

## Project
RAG system that generates tailored resumes for internship applications using LlamaIndex + Google Gemini.
The system must produce resumes that are faithful to the candidate's verified data, complete for the target job, and readable by a recruiter.

## Current phase
**Research & refactoring** (phases P0–P11 in `docs/agent_prompts.md`, governed by `docs/research_plan.md`).
Phases 1–6 of the original build are complete. Do not add features outside the current task. Each session works on ONE phase only; never start the next one without explicit authorization.

## Stack
- Python 3.11+ (the Docker image uses 3.12), LlamaIndex, Google Gemini, ChromaDB, Gradio, Tectonic (LaTeX → PDF), Jinja2, Pydantic v2
- Embeddings: `models/gemini-embedding-001`
- LLMs: configured **only** through `src/config.py` / `.env` with pinned model IDs (see "API usage and models"). Do not assume which model is configured; read the settings.

## Code Standards
- Pydantic v2 for all schemas and settings
- Type hints required on all functions
- Google-style docstrings on public classes and functions
- Absolute imports from `src/`
- Identifiers, comments, docstrings, logs and documentation in English (ADR-006). Runtime data values (candidate profile, knowledge base documents) and Gradio UI labels may stay in Portuguese.

## Required Documentation
- Every significant change is recorded in `docs/decisions_log.md` as an ADR (context, decision, rationale, consequences, and the alternatives that were rejected).
- At the end of every work session, update `docs/development_diary.md` using the existing entry format (What was done / Decisions made / Model used / Challenges / Next steps).
- Experiment results go in `docs/experiments/EXX_<name>.md` (tables and commands only). The **Interpretation** and **Conclusions** sections are written by the human, never by the agent.
- `docs/lessons.md` is written by the human only.
- Keep docs consistent with code. If you find a divergence, list it in your report; do not silently pick one.

## Project Structure
Follow the directory structure in `docs/architecture.md`. Do not create files outside it without justification. Approved additions for this phase:
`src/verification/`, `src/evaluation/` (new modules), `src/generation/variants/`, `tests/golden/`, `data/eval/dev/`, `data/eval/real/`, `docs/experiments/`, `runs/` (run outputs, git-ignored), `blind/` (blind-rating pairs, git-ignored).

## Quality
- Unit tests for all business logic. Tests run offline (mocks or synthetic data); no test may call the real API.
- Handle edge cases (job without requirements, incomplete profile, special characters, API failure).
- **The generated resume must NEVER invent information.** Use only data from `data/candidate_profile.yaml` and the verified atomic facts in `data/candidate_facts.yaml`.
- Structural tests (schema, rendering) do not prove truthfulness. Truthfulness is checked by `tests/golden/` and `src/verification/`.

## Security & Privacy
- The agent must NEVER read, display, print or access `.env` files or environment variables containing real credentials.
- Automated tests and local checks must use mocks or synthetic data.
- Contact data (phone, email, links) must not be sent to an LLM. Once render-time injection is implemented (phase P8), this is enforced by tests. Until then, do not add new code paths that send it.

## Research & Refactoring Rules

### Protected paths (never edit, create files inside, or delete without explicit approval in the prompt)
- `data/candidate_profile.yaml` and `data/candidate_facts.yaml` (source of truth about the candidate).
- `data/eval/` (benchmark data) and `tests/golden/` (regression checks), once the human has approved them.
- `docs/research_plan.md`, section 7 (decision thresholds), once frozen.
- Existing tests, metric definitions and evaluators: never change them to make something pass. If you believe one is wrong, STOP, explain why, and wait for approval.
- `data/heldout/` and anything under `$HELDOUT_DIR`: never read, list, open or reference their contents. Never set or use `ALLOW_HELDOUT`.
- `.env` and any file with credentials.

### Evidence
- Every claim about results ("tests pass", "score improved", "issue fixed") must come with the exact command that was run and its real, unedited output.
- Never write claims such as "zero hallucination", "100% faithful" or "production ready" in code, docs, README or badges unless a validated metric supports them (validated = the judge passed the validation described in the research plan).
- Report negative and inconclusive results as prominently as positive ones.
- If you could not verify something, write "not verified" instead of assuming.

### Workflow
- One change per commit / PR. Measure before and after and record both numbers.
- Work only on the task in the current prompt. If something is ambiguous, ask instead of assuming.
- Do not add dependencies without asking; state the package, version and reason.
- Do not weaken existing behavior (for example `allow_fallback` semantics) while refactoring.

### API usage and models
- Use pinned model IDs from settings. Never use `-latest` aliases. Never hardcode model IDs outside `src/config.py`.
- Target configuration after phase P1: `GENERATION_MODEL=gemini-3.5-flash-lite` for development and benchmarks; `gemini-3.8-flash` allowed as an override for real resume generation; `JUDGE_MODEL=gemini-3.1-flash-lite`. Pro models are not available on the free tier; do not assume them.
- Generator and judge must be different models.
- Before any run that calls the API, print the estimated number of calls per model and stop for approval if it exceeds 100 calls. Respect free-tier daily quotas; runners must implement `--dry-run` and `--max-calls`.
- Every experiment run writes a manifest: git SHA, variant, exact model IDs, temperature, judge model and prompt version, dataset hash, seed, number of API calls.

### Reporting format (end of every task)
1. Files changed (list).
2. Commands run + real output (tests, linters, runs).
3. What could not be verified.
4. Decisions taken or proposed (for the ADR).
5. Questions for the human.
