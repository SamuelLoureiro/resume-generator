# Log de Decisões Técnicas (ADRs)

## ADR-001: Google Gemini como LLM Provider
- **Data:** 2026-09-22
- **Status:** Aceito
- **Contexto:** Necessidade de escolher um LLM provider para geração e embeddings
- **Decisão:** Google Gemini (modelos 2.5 Flash e Pro) via API
- **Justificativa:** Usuário possui Google AI Pro, sem custo adicional. Qualidade competitiva com GPT-4o
- **Consequências:** Dependência do ecossistema Google; boa integração com LlamaIndex

## ADR-002: LlamaIndex como Framework RAG
- **Data:** 2026-09-22
- **Status:** Aceito
- **Contexto:** Escolha entre LangChain e LlamaIndex para o pipeline RAG
- **Decisão:** LlamaIndex
- **Justificativa:** API mais focada e intuitiva para RAG; melhor abstração para indexação e retrieval
- **Consequências:** Menor flexibilidade para chains complexas, mas suficiente para o caso de uso

## ADR-003: PDF via LaTeX para saída
- **Data:** 2026-09-22
- **Status:** Aceito
- **Contexto:** Formato de saída do currículo gerado
- **Decisão:** PDF gerado via compilação LaTeX (Jinja2 template → .tex → pdflatex → .pdf)
- **Justificativa:** Qualidade tipográfica superior; controle preciso de layout; padrão acadêmico/profissional
- **Consequências:** Requer instalação de distribuição LaTeX (texlive); maior complexidade que DOCX

## ADR-004: Gradio como Interface
- **Data:** 2026-09-22
- **Status:** Aceito
- **Contexto:** Framework de UI para demonstração e uso do sistema
- **Decisão:** Gradio ao invés de Streamlit
- **Justificativa:** Deploy fácil no HuggingFace Spaces; API simples; bom para demos de ML
- **Consequências:** Menos flexibilidade de layout que Streamlit, mas suficiente

## ADR-005: ChromaDB como Vector Store
- **Data:** 2026-09-22
- **Status:** Aceito
- **Contexto:** Necessidade de armazenar e buscar embeddings
- **Decisão:** ChromaDB com persistência local
- **Justificativa:** Leve, sem infraestrutura externa, boa integração com LlamaIndex
- **Consequências:** Não escala para milhões de documentos, mas o dataset é pequeno
