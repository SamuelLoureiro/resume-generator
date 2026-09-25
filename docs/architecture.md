# Architecture — Resume Generator with RAG

## Overview

RAG-based system that generates tailored resumes for internship positions,
combining candidate personal data with specialized knowledge on recruitment
and resume best practices.

## Stack

| Component       | Technology                      |
|-----------------|---------------------------------|
| Language        | Python 3.11+                    |
| LLM             | Google Gemini 2.5 Flash/Pro     |
| RAG Framework   | LlamaIndex                      |
| Embeddings      | text-embedding-004 (Google)     |
| Vector Store    | ChromaDB                        |
| Output          | PDF via LaTeX (Jinja2)          |
| Interface       | Gradio                          |
| Testing         | pytest + RAGAS                  |

## System Flow

```
Input:
  candidate_profile.yaml + job description + LaTeX template
    ↓
Ingestion (once):
  knowledge_base/ → SimpleDirectoryReader → SentenceSplitter → Embeddings → ChromaDB
    ↓
Retrieval (per job):
  Job query → Hybrid Search (Vector + BM25) → Top-5 relevant chunks
    ↓
Generation:
  Prompt (candidate + job + chunks + template) → Gemini → Structured content
    ↓
Formatting:
  Jinja2 → .tex file → pdflatex → Final PDF
    ↓
Output:
  output/resume_<company>_<date>.pdf
```

## Directory Structure

```
gerador_curriculos/
├── .agents/                       # AGY customizations
├── src/
│   ├── config.py
│   ├── data/                      # Pydantic schemas
│   ├── ingestion/                 # Loader + Indexer
│   ├── retrieval/                 # Hybrid Retriever
│   ├── generation/                # Prompts + Chain + Formatter
│   ├── knowledge_base/            # Knowledge docs (.md)
│   └── app.py                     # Gradio
├── templates/                     # LaTeX template
├── data/                          # Candidate profile + job postings
├── tests/
├── notebooks/
├── docs/
└── output/                        # Generated PDFs
```

## Development Phases

1. **Foundation & Data** — Setup, schemas, knowledge base
2. **RAG Core** — Ingestion, indexing, retrieval
3. **Generation & Formatting** — Prompts, chain, LaTeX → PDF
4. **Interface** — Gradio app
5. **Evaluation** — RAGAS, tuning
6. **Portfolio & Deploy** — README, Docker, HuggingFace

For details on each phase, refer to the full project plan.
