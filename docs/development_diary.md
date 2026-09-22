# Diário de Desenvolvimento

## 2026-09-22 — Planejamento Inicial
- **O que foi feito:** Definição completa da arquitetura, stack tecnológica e plano de 6 fases
- **Decisões tomadas:**
  - LLM: Google Gemini (AI Pro)
  - Framework RAG: LlamaIndex
  - Saída: PDF via LaTeX
  - Interface: Gradio
  - Vector Store: ChromaDB
  - Embeddings: text-embedding-004 do Google
- **Modelo usado:** Claude Opus (planejamento)
- **Desafios:** Nenhum nesta fase
- **Próximos passos:** Iniciar Fase 1 — setup do projeto (pyproject.toml, schemas, knowledge base)

## 2026-09-22 — Tarefa 1.1: Inicialização do Projeto e Configuração
- **O que foi feito:**
  - Configuração do `pyproject.toml` com LlamaIndex, Google Gemini, ChromaDB, Gradio, Jinja2, Pydantic, etc.
  - Criação do `.env.example` com template de chaves e variáveis do sistema
  - Criação do `.gitignore` para Python, ambientes virtuais, LaTeX temporários e ChromaDB
  - Implementação de `src/__init__.py` e `src/config.py` com Pydantic Settings v2
  - Criação da árvore de diretórios base (`src/data/`, `src/ingestion/`, `src/retrieval/`, `src/generation/`, `src/knowledge_base/`, `templates/`, `data/job_postings/`, `output/`, `tests/`)
- **Decisões tomadas:**
  - Inclusão de `pydantic-settings` para gestão robusta de configurações baseadas em `.env`
  - Separação de submódulos em `src/` respeitando a arquitetura
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Tarefa 1.2 — Schemas Pydantic (`src/data/*.py`)
