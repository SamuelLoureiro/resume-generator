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
