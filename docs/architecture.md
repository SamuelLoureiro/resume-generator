# Arquitetura — Gerador de Currículos com RAG

## Visão Geral

Sistema RAG que gera currículos personalizados para vagas de estágio,
combinando dados pessoais do candidato com conhecimento especializado
em recrutamento e boas práticas de currículo.

## Stack

| Componente | Tecnologia |
|---|---|
| Linguagem | Python 3.11+ |
| LLM | Google Gemini 2.5 Flash/Pro |
| Framework RAG | LlamaIndex |
| Embeddings | text-embedding-004 (Google) |
| Vector Store | ChromaDB |
| Saída | PDF via LaTeX (Jinja2) |
| Interface | Gradio |
| Testes | pytest + RAGAS |

## Fluxo do Sistema

```
Entrada:
  candidate_profile.yaml + descrição da vaga + template LaTeX
    ↓
Ingestão (uma vez):
  knowledge_base/ → SimpleDirectoryReader → SentenceSplitter → Embeddings → ChromaDB
    ↓
Retrieval (por vaga):
  Query da vaga → Hybrid Search (Vector + BM25) → Top-5 chunks relevantes
    ↓
Geração:
  Prompt (candidato + vaga + chunks + template) → Gemini → Conteúdo estruturado
    ↓
Formatação:
  Jinja2 → arquivo .tex → pdflatex → PDF final
    ↓
Saída:
  output/curriculo_<empresa>_<data>.pdf
```

## Estrutura de Diretórios

```
gerador_curriculos/
├── .agents/                       # Customizações AGY
├── src/
│   ├── config.py
│   ├── data/                      # Schemas Pydantic
│   ├── ingestion/                 # Loader + Indexer
│   ├── retrieval/                 # Hybrid Retriever
│   ├── generation/                # Prompts + Chain + Formatter
│   ├── knowledge_base/            # Docs de conhecimento (.md)
│   └── app.py                     # Gradio
├── templates/                     # Template LaTeX
├── data/                          # Perfil do candidato + vagas
├── tests/
├── notebooks/
├── docs/
└── output/                        # PDFs gerados
```

## Fases de Desenvolvimento

1. **Fundação e Dados** — Setup, schemas, knowledge base
2. **RAG Core** — Ingestão, indexação, retrieval
3. **Geração e Formatação** — Prompts, chain, LaTeX → PDF
4. **Interface** — Gradio app
5. **Avaliação** — RAGAS, tuning
6. **Portfólio e Deploy** — README, Docker, HuggingFace

Para detalhes de cada fase, consultar o plano completo do projeto.
