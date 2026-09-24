# Otimização para Sistemas de Triagem Automática (ATS)

## 1. O que são os ATS (Applicant Tracking Systems)?
Sistemas ATS (como Gupy, Workday, Greenhouse, Taleo e Lever) são softwares corporativos usados por empresas e consultorias para receber, parsear, categorizar e ranquear milhares de currículos antes mesmo de qualquer triagem humana.

Mais de 75% dos currículos em grandes corporações e startups são descartados na fase de triagem do ATS por incompatibilidade de formato ou baixa pontuação semântica com a vaga.

---

## 2. Princípios de Compatibilidade com Parsers de ATS

### O Que os Robôs de ATS Conseguem Ler Perfeitamente
- **Estrutura Linear:** Texto contínuo, cabeçalhos padronizados e listas com marcadores simples (`\textbullet`).
- **Nomenclatura Convencional de Seções:** Use nomes consagrados como *Objetivo Profissional*, *Formação Acadêmica*, *Experiência*, *Projetos*, *Habilidades Técnicas*, *Idiomas*. Títulos "criativos" (ex: "Minha Jornada", "O que já fiz") confundem os parsers e fazem o candidato perder pontuação.
- **Texto Vetorial Selecionável:** PDFs gerados via LaTeX ou processadores de texto onde o texto pode ser selecionado e copiado diretamente. (Nunca use imagem de currículo ou exportação rasterizada).

### O Que Quebra ou Reduz a Pontuação no ATS
- **Tabelas Complexas e Colunas Múltiplas Flutuantes:** Muitos parsers leem tabelas de ponta a ponta horizontalmente, misturando o texto da coluna esquerda com a da coluna direita.
- **Gráficos e Barras de Progresso de Habilidades:** Elementos visuais como "Python: 80%" ou "3 estrelas em SQL" são invisíveis para os robôs e passam imagem de amadorismo para recrutadores técnicos.
- **Caixas de Texto e Headers/Footers Rígidos:** Informações cruciais colocadas no cabeçalho ou rodapé físico da página podem ser ignoradas pelo parser.

---

## 3. Estratégia de Semântica e Palavras-Chave (Keyword Matching)

O algoritmo do ATS compara o texto do currículo com a descrição da vaga anunciada. Para maximizar a aderência:

1. **Correspondência Exata e Variações:**
   - Se a vaga pede "Python, SQL e Docker", esses termos exatos devem constar no currículo tanto na seção de habilidades quanto no contexto dos projetos ou experiências.
   - Use a forma extensa e a sigla quando relevante (ex: *Processamento de Linguagem Natural (PLN)*, *Inteligência Artificial (IA)*).

2. **Densidade Equilibrada (Contextual Keyword Density):**
   - Não basta listar palavras-chave isoladas numa lista no final.
   - Os algoritmos modernos (especialmente com NLP) atribuem peso maior a palavras-chave que aparecem associadas a ações e resultados em bullet points (ex: *"Desenvolveu modelos de Machine Learning utilizando scikit-learn"* pontua mais que apenas *"scikit-learn"* numa lista solta).

3. **Anti-Pattern: "Keyword Stuffing" ou Texto Oculto:**
   - Técnicas antigas como colar requisitos da vaga em texto branco ou fonte minúscula são detectadas instantaneamente pelos parsers modernos e causam desclassificação automática por fraude.

---

## 4. Checklist ATS para Currículos Gerados
- [ ] O arquivo está em PDF gerado diretamente a partir de código/texto legível.
- [ ] O nome do arquivo é profissional: `Curriculo_Nome_Sobrenome.pdf`.
- [ ] Os títulos das seções seguem o vocabulário padrão da indústria.
- [ ] Todos os requisitos essenciais da vaga estão refletidos no texto com base em fatos reais do candidato.
- [ ] Não há tabelas invisíveis, ícones em excesso ou colunas flutuantes conflitantes.
