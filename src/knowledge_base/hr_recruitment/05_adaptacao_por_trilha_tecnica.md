# Estratégias de Adaptação de Currículo por Trilha Técnica

## 1. O Princípio da Aderência Temática
O pipeline RAG deve identificar a **trilha técnica predominante** da vaga e calibrar a ênfase das seções do currículo para colocar em primeiro plano as competências mais afins à função desejada.

---

## 2. Diretrizes por Trilha de Especialidade

### Trilha 1: Inteligência Artificial, LLMs e Engenharia de RAG
- **O que os recrutadores dessa área priorizam:**
  - Experiência prática com frameworks de orquestração de LLMs (`LlamaIndex`, `LangChain`).
  - Conhecimento em bancos de dados vetoriais (`ChromaDB`, `Pinecone`, `FAISS`, `Qdrant`).
  - Avaliação de modelos de linguagem (métricas do framework `RAGAS`, acurácia, alucinação, relevância).
  - Estratégias de busca híbrida (Embeddings densos + BM25) e chunking de texto.
  - Engenharia de prompts estruturada e chamadas de função (function calling).
- **Como adaptar no currículo:**
  - O objetivo profissional deve citar textualmente interesse em IA Generativa e RAG.
  - O projeto do Gerador de Currículos RAG deve ser o primeiro item em destaque na seção de projetos.
  - Na seção de habilidades, colocar *LlamaIndex*, *Google Gemini*, *ChromaDB* e *PyTorch* no topo.

### Trilha 2: Ciência e Engenharia de Dados
- **O que os recrutadores dessa área priorizam:**
  - Fluência absoluta em Python e SQL para manipulação e consulta de dados relacionais e analíticos.
  - Bibliotecas de processamento: `Pandas`, `NumPy`, `Polars`, `Scikit-Learn`.
  - Construção de pipelines de extração, transformação e carga (ETL).
  - Limpeza, tratamento de valores faltantes e análise exploratória de dados (EDA).
  - Criação de dashboards ou relatórios para tomada de decisão.
- **Como adaptar no currículo:**
  - Enfatizar volume de dados tratados em cada experiência ou projeto (ex: *50.000 registros*).
  - Destacar bancos de dados utilizados (`PostgreSQL`, `SQLite`, `BigQuery`).
  - Ressaltar métricas de precisão, recall, F1 e visualização.

### Trilha 3: Engenharia de Software e Desenvolvimento Backend
- **O que os recrutadores dessa área priorizam:**
  - Criação e consumo de APIs RESTful estruturadas (`FastAPI`, `Flask` ou `Django`).
  - Modelagem e integração com bancos de dados relacionais (`PostgreSQL`) com ORM (`SQLAlchemy`).
  - Boas práticas: tipagem estática com Pydantic, testes automatizados (`pytest`), tratamento de erros e exceções.
  - Conteinerização básica com Docker e controle de versão profissional com Git/GitHub.
- **Como adaptar no currículo:**
  - Destacar a arquitetura em camadas dos projetos, cobertura de testes e modularidade.
  - Enfatizar a capacidade de construir sistemas estáveis e bem documentados.

---

## 3. Diretriz para a Síntese do LLM no RAG
Quando a vaga for fornecida pelo usuário:
1. O sistema deve extrair as competências nucleares da vaga (ex: "estágio com foco em IA").
2. Filtrar do perfil do candidato (`candidate_profile.yaml`) os projetos e conquistas com maior sobreposição semântica.
3. Posicionar os termos técnicos da vaga nos primeiros bullet points de projetos e experiências, garantindo que todo dado gerado seja verídico e fundamentado.
