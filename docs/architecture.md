# Architecture — Resume Generator with RAG & Closed-Loop Verification

## Overview

A grounded, empirical RAG system that generates tailored resumes for internship positions by synthesizing verified candidate data with specialized recruitment guidelines, verified through a closed-loop post-generation verifier that eliminates hallucinations and verb inflation.

## Stack

| Component | Technology | Description |
|---|---|---|
| Language | Python 3.12 (3.11+) | Strict type hinting & Pydantic v2 |
| Generator LLM | Google Gemini (`gemini-3.5-flash-lite`) | Primary generation model (temp: 0.3) |
| Judge LLM | Google Gemini (`gemini-3.1-flash-lite`) | Independent atomic claim evaluator (temp: 0.0) |
| RAG Framework | LlamaIndex 0.12+ | Document loading, node splitting, retriever wiring |
| Embeddings | Google `models/gemini-embedding-001` | Dense vector embeddings for recruitment knowledge |
| Vector Store | ChromaDB (Persistent) | Local persistent vector storage in `chroma_db/` |
| Sparse Search | BM25 | In-memory token-level keyword search |
| Rank Fusion | Reciprocal Rank Fusion (RRF, k=60) | Unbiased score combination across dense and sparse spaces |
| Verification | Custom Deterministic + LLM Judge | M1 (Fabrication), M2 (Verb ladder), M4 (Keywords), M5 (Format) |
| Output | LaTeX → PDF (Jinja2 + Tectonic) | Single-page ATS-optimized typographical output |
| Interface | Gradio 6.28.0 | Web application with real-time PDF preview and transparency report |
| Testing | pytest | 424 automated tests running 100% offline |

## System Flow

```
Input:
  Candidate Profile + Candidate Facts (with Scope Ceilings) + Target Job Posting
    ↓
Knowledge Retrieval:
  Job Query → Hybrid Search (Dense ChromaDB + BM25 Sparse) → RRF k=60 → Top-5 Chunks
    ↓
Privacy Scrubbing (SEC-01):
  Candidate contact info (email, phone, URLs, address) stripped before prompt transmission
    ↓
Generation (Round 0):
  System Prompt + Candidate Facts + Job Requirements + Retrieved Context → gemini-3.5-flash-lite
    ↓
Verification Loop (V1):
  Deterministic checks (M1a-c, M2, M4, M5) + Isolated Claim Judge (M1d: gemini-3.1-flash-lite)
  ├─ 0 Defects → PASS (clean@0)
  ├─ Defects Found (Rounds 1–2) → Error-Guided Regeneration Prompt → Retry (clean@1 / clean@2)
  └─ Residual Defects → Deterministic Repair Surgery (repair_resume)
       ├─ Repaired cleanly → PASS (repaired)
       └─ Residual issues persist → Grounded Deterministic Floor (fallback B0)
    ↓
Formatting & Rendering:
  Jinja2 Template (resume.tex.j2) + Contact Injection → Tectonic TeX Engine → 1-Page PDF
    ↓
Output:
  output/resume_<company>_<date>.pdf + output/resume_<company>_<date>.tex
```

## Directory Structure

```
gerador_curriculos/
├── app.py                         # Root entrypoint for Hugging Face Spaces / Gradio
├── pyproject.toml                 # Packaging & dependencies
├── requirements.txt               # Frozen dependencies
├── Dockerfile                     # Containerization with precompiled Tectonic
├── docker-compose.yml             # Local Docker Compose setup
├── data/
│   ├── candidate_profile.yaml     # Protected source of truth for candidate background
│   ├── candidate_facts.yaml       # Atomic verified facts with 4-level scope ceilings
│   └── eval/
│       ├── MANIFEST.sha256        # Dataset integrity hash
│       └── dev/                   # Dev test cases across 5 technical tracks
├── src/
│   ├── config.py                  # Pydantic Settings, model pinning & API guards
│   ├── app.py                     # Gradio application & action workflows
│   ├── data/                      # Pydantic v2 schemas (Candidate, Job, Resume, Facts)
│   ├── ingestion/                 # Markdown loader & ChromaDB vector indexer
│   ├── retrieval/                 # Hybrid retriever (Dense + BM25 + RRF) & pipeline
│   ├── generation/                # Prompts, chain, LaTeX formatter, and variants
│   │   └── variants/              # B0 (Fallback), B1 (RAG), B3 (Full KB), V1 (Verified)
│   ├── verification/              # Deterministic checkers (M1-M5), repair, and issues layer
│   ├── evaluation/                # Claim-level judge (M1d) & synthetic defect injection
│   └── knowledge_base/            # 12 Markdown guides across 5 tracks
├── templates/
│   └── resume.tex.j2              # Multilingual Jinja2 LaTeX template
├── tests/
│   ├── golden/                    # Golden set regression checks (Amazon SDE fixture)
│   └── ...                        # 425 offline unit and integration tests
├── docs/
│   ├── architecture.md            # System architecture & stack
│   ├── research_plan.md           # Research hypotheses and frozen decision protocol
│   ├── decisions_log.md           # Architecture Decision Records (ADR-001 to ADR-026)
│   ├── development_diary.md       # Chronological development diary
│   ├── lessons.md                 # Qualitative learnings
│   └── experiments/               # Experiment reports (E00, E01, E02, E03, E04)
└── output/                        # Generated PDFs and TeX files
```
