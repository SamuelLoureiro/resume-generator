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

## 2026-09-23 — Tarefa 1.2: Modelagem de Schemas Pydantic e Regras de Segurança
- **O que foi feito:**
  - Adicionadas regras de segurança e privacidade em `.agents/GEMINI.md` (blindagem do `.env` contra inspeção de agentes).
  - Implementação de `src/data/candidate.py` com schemas completos (`CandidateProfile`, `ContactInfo`, `Education`, `Experience`, `Project`, `Skills`, etc.) e suporte a importação/exportação YAML.
  - Implementação de `src/data/job_posting.py` com estrutura de requisitos, diferenciais e gerador de queries de busca semântica (`to_search_query`).
  - Implementação de `src/data/resume.py` com suporte à sanitização/escape automático de caracteres especiais de LaTeX (`&`, `%`, `$`, `#`, `_`, etc.) via `to_latex_context()`.
  - Exportação unificada dos modelos em `src/data/__init__.py`.
  - Criação de suíte de testes unitários em `tests/test_schemas.py` com 6 testes aprovados (100% de sucesso).
- **Decisões tomadas:**
  - Sanitização profunda de strings para LaTeX em nível de modelo de dados para prevenir falhas de compilação no Jinja2/pdflatex.
  - Execução e validação de testes 100% offline, sem necessidade de credenciais de API.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Tarefa 1.3 — Criação do template `data/candidate_profile.yaml` (dados do candidato) e Tarefa 1.4 — Template LaTeX (`templates/resume.tex.j2`)

## 2026-09-23 — Tarefa 1.3: Criação da Base de Perfil do Candidato (YAML)
- **O que foi feito:**
  - Criação do arquivo estruturado e comentado `data/candidate_profile.yaml` com todas as seções mapeadas: contato, resumo, educação (graduação, disciplinas, bolsas), experiências (IC, projetos), portfólio de projetos práticos em IA/RAG, habilidades técnicas/soft skills categorizadas, idiomas e certificações.
  - Adição de teste unitário automatizado em `tests/test_schemas.py` garantindo que o arquivo YAML default seja sempre 100% válido contra o schema `CandidateProfile`.
  - Suíte de testes passando com 7/7 sucessos.
- **Decisões tomadas:**
  - Estruturação do YAML em português nos valores e inglês nas chaves, mantendo facilidade de preenchimento para o usuário e aderência estrita aos modelos Pydantic.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Tarefa 1.4 — Template LaTeX (`templates/resume.tex.j2`) e Tarefas 1.5/1.6 — Curadoria da base de conhecimento (boas práticas e RH)
