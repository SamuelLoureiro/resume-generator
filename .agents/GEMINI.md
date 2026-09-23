# Gerador de Currículos RAG - Project Rules

## Projeto
Sistema RAG que gera currículos personalizados para vagas de estágio usando LlamaIndex + Google Gemini.

## Stack
- Python 3.11+, LlamaIndex, Google Gemini (AI Pro), ChromaDB, Gradio, LaTeX (PDF)
- Embeddings: `models/text-embedding-004`
- LLM: `gemini-2.5-flash` (dev) / `gemini-2.5-pro` (produção)

## Padrões de Código
- Pydantic v2 para todos os schemas e configurações
- Type hints obrigatórios em todas as funções
- Docstrings Google-style em classes e funções públicas
- Imports absolutos a partir de `src/`
- Nomes de variáveis e comentários em inglês, docs de usuário em português

## Documentação Obrigatória
- Toda mudança significativa deve ser registrada em `docs/decisions_log.md`
- Ao final de cada sessão de trabalho, atualizar `docs/development_diary.md`
- Seguir os formatos definidos nesses arquivos

## Estrutura do Projeto
Respeitar a estrutura de diretórios definida em `docs/architecture.md`.
Não criar arquivos fora da estrutura sem justificativa.

## Qualidade
- Testes unitários para toda lógica de negócio
- Tratar edge cases (vaga sem requisitos, perfil incompleto, etc.)
- O currículo gerado NUNCA deve inventar informações — usar apenas dados de `data/candidate_profile.yaml`

## Segurança e Privacidade
- O agente NUNCA deve ler, exibir, imprimir ou acessar arquivos `.env` ou variáveis de ambiente com credenciais reais.
- Testes automatizados e verificações locais devem utilizar mocks ou dados sintéticos.
