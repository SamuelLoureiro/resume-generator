---
name: resume-rag
description: >-
  Contexto completo e instruções do projeto Gerador de Currículos com RAG.
  Ative esta skill quando estiver trabalhando em qualquer parte do projeto.
---

# Resume RAG Generator — Contexto do Projeto

## Visão Geral
Sistema baseado em Retrieval-Augmented Generation (RAG) que gera currículos
personalizados para vagas de estágio. Combina dados pessoais do candidato,
detalhes da vaga, e conhecimento especializado em recrutamento.

## Stack Tecnológica
| Componente | Tecnologia |
|---|---|
| LLM | Google Gemini 2.5 Flash/Pro via `llama-index-llms-gemini` |
| Embeddings | `models/text-embedding-004` via `llama-index-embeddings-gemini` |
| Framework RAG | LlamaIndex (`llama-index-core`) |
| Vector Store | ChromaDB (`llama-index-vector-stores-chroma`) |
| Saída | PDF via LaTeX (Jinja2 + pdflatex) |
| Interface | Gradio |
| Testes | pytest + RAGAS |

## Estrutura de Diretórios
```
src/
├── config.py                  # Settings (Pydantic Settings)
├── data/                      # Schemas Pydantic (candidate, job_posting, resume)
├── ingestion/                 # loader.py, indexer.py
├── retrieval/                 # retriever.py (hybrid: vector + BM25)
├── generation/                # prompts.py, chain.py, formatter.py
├── knowledge_base/            # .md files com conhecimento de RH e currículos
│   ├── resume_best_practices/
│   ├── hr_recruitment/
│   └── resume_examples/
└── app.py                     # Gradio interface
```

## Pipeline RAG
1. **Ingestão:** `SimpleDirectoryReader` → `SentenceSplitter` (512 tokens, 50 overlap) → Gemini Embeddings → ChromaDB
2. **Retrieval:** Hybrid search (vector + BM25), top_k=5, com metadata filtering
3. **Geração:** Multi-step prompting (análise da vaga → matching → otimização → geração)
4. **Formatação:** Jinja2 renderiza template LaTeX → pdflatex compila → PDF

## Fases de Desenvolvimento
Consultar `docs/architecture.md` para o plano completo com 6 fases.

## Regras Importantes
- NUNCA inventar experiências ou dados do candidato — usar apenas `data/candidate_profile.yaml`
- Documentar decisões em `docs/decisions_log.md`
- Atualizar diário em `docs/development_diary.md` ao final de cada sessão
