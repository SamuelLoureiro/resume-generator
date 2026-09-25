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

## 2026-09-23 — Tarefa 1.4: Criação do Template LaTeX Dinâmico (Jinja2)
- **O que foi feito:**
  - Criação do template LaTeX modular em `templates/resume.tex.j2` otimizado para currículos de estágio em 1 página.
  - Utilização de delimitadores Jinja2 não-conflitantes (`<% ... %>` para blocos e `<< ... >>` para variáveis) eliminando qualquer colisão com chaves (`{}`) e comandos nativos do LaTeX.
  - Implementação de seções: Cabeçalho com links (e-mail, LinkedIn, GitHub, portfólio), Objetivo Profissional alinhado à vaga, Formação Acadêmica, Experiências com bullets de impacto e tecnologias, Projetos em Destaque, Habilidades Técnicas categorizadas, Idiomas e Certificações.
  - Criação de teste unitário em `tests/test_template.py` validando renderização completa, injeção de dados de `TailoredResume.to_latex_context()` e escape de caracteres especiais.
  - Suíte de testes atualizada: 8/8 testes passando com sucesso no `pytest`.
- **Decisões tomadas:**
  - Adoção de pacotes padrão e leves do LaTeX (`article`, `geometry`, `titlesec`, `enumitem`, `hyperref`, `xcolor`), compatíveis com qualquer distribuição LaTeX sem necessidade de fontes ou pacotes proprietários.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Tarefas 1.5 e 1.6 — Curadoria da base de conhecimento (boas práticas de currículo e recrutamento de estágio em `src/knowledge_base/`)

## 2026-09-24 — Tarefa 1.5: Curadoria da Base de Conhecimento — Boas Práticas de Currículo
- **O que foi feito:**
  - Criação de 5 documentos markdown técnicos e modulares em `src/knowledge_base/resume_best_practices/`:
    - `01_estrutura_curriculo_estagio.md`: Regra de 1 página, ordem hierárquica ideal para estudantes (educação no topo) e escaneabilidade visual.
    - `02_metodo_star_xyz_bullets.md`: Fórmula XYZ do Google, método STAR e estratégias para quantificar resultados técnicos sem experiência corporativa prévia.
    - `03_verbos_de_acao_e_vocabulario.md`: Catálogo de verbos de ação fortes categorizados por domínio (desenvolvimento, IA/dados, performance, liderança) e lista negra de palavras fracas/clichês.
    - `04_otimizacao_ats.md`: Arquitetura dos robôs de triagem ATS, correspondência contextual de palavras-chave e checklist de compatibilidade.
    - `05_erros_comuns_e_red_flags.md`: Red flags fatais na triagem dos 6 segundos (erros ortográficos, currículo genérico, alucinação de competências).
  - Execução da suíte de testes: 8/8 testes passando.
- **Decisões tomadas:**
  - Estruturação dos textos com cabeçalhos semânticos claros para otimizar o particionamento em chunks pelo `SentenceSplitter` do LlamaIndex na Fase 2.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Tarefa 1.6 — Curadoria da base de conhecimento de RH e recrutamento de estágio (`src/knowledge_base/hr_recruitment/`)

## 2026-09-24 — Tarefa 1.6: Curadoria da Base de Conhecimento — Recrutamento e RH de Estágio
- **O que foi feito:**
  - Criação de 5 documentos markdown especializados em `src/knowledge_base/hr_recruitment/`:
    - `01_o_que_recrutadores_procuram_em_estagio.md`: Foco em potencial de aprendizado (learning agility), fundamentos sólidos e senso de dono (ownership).
    - `02_diferencas_big_techs_vs_startups.md`: Critérios de avaliação em Big Techs (escala, arquitetura, algoritmos) vs Startups (velocidade, end-to-end, MVPs e pragmatismo).
    - `03_soft_skills_e_diferenciais_competitivos.md`: Princípio "Mostre, Não Apenas Diga" (Show, Don't Tell) para comunicação, trabalho em equipe e curiosidade intelectual.
    - `04_valorizacao_experiencias_academicas_e_projetos.md`: Como converter Iniciação Científica, Empresa Júnior, Monitoria e Projetos Pessoais em experiência de alto valor no mercado corporativo.
    - `05_adaptacao_por_trilha_tecnica.md`: Diretrizes de priorização semântica por trilhas (Inteligência Artificial / RAG, Engenharia de Dados, Backend).
  - Implementação de teste unitário em `tests/test_knowledge_base.py` validando presença, extensão e formato de todos os documentos da base de conhecimento.
  - Suíte de testes atualizada: 9/9 testes passando com 100% de sucesso.
- **Decisões tomadas:**
  - Encerramento completo de todos os entregáveis da **Fase 1 (Fundação e Dados)** do projeto.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Nenhum
- **Próximos passos:** Iniciar a **Fase 2 — Pipeline RAG Core** (Loader com `SimpleDirectoryReader`, indexação com `SentenceSplitter`, embeddings com `models/text-embedding-004`, vector store ChromaDB e retriever híbrido).

## 2026-09-25 — Tarefa 2.1: Implementação do Document Loader (LlamaIndex)
- **O que foi feito:**
  - Instalação e configuração de dependências do LlamaIndex (`llama-index-core`, `llama-index-readers-file`, `llama-index-llms-gemini`, `llama-index-embeddings-gemini`, `llama-index-vector-stores-chroma`, `chromadb`) no ambiente virtual `.venv`.
  - Implementação de `src/ingestion/loader.py` com a classe `KnowledgeBaseLoader` e função auxiliar `extract_title_from_markdown`:
    - Integração de `SimpleDirectoryReader` para varredura recursiva de arquivos Markdown.
    - Enriquecimento automático de metadados em cada documento (`category`, `topic`, `file_name`).
    - Métodos para carga seletiva por categoria (`load_category`) e carga agregada (`load_all_documents`).
  - Criação de testes unitários em `tests/test_ingestion.py` cobrindo extração de títulos, carga de categorias, agregação de documentos, diretórios customizados e tratamento de exceções.
  - Suíte de testes atualizada: 15/15 testes passando com 100% de sucesso.
- **Decisões tomadas:**
  - Enriquecimento dos metadados dos nós na carga para permitir filtragem contextual precisa no ChromaDB durante o retrieval.
- **Modelo usado:** Gemini Flash (execução)
- **Desafios:** Resolução de dependências gRPC resolvida com sucesso pelo pip.
- **Próximos passos:** Tarefa 2.2 — Indexação com `SentenceSplitter` e geração de embeddings (`src/ingestion/indexer.py`).
