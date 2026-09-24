# Erros Comuns e Red Flags Fatais em Currículos de Estágio

## 1. O Filtro dos 6 Segundos
Pesquisas consagram que recrutadores humanos realizam um primeiro escaneamento visual em 6 a 10 segundos. Pequenos descuidos ou elementos fora do padrão são suficientes para descartar o candidato nessa triagem preliminar.

---

## 2. As Principais "Red Flags" que Eliminam Candidatos

### 1. Erros Gramaticais e de Digitação
- **Gravidade:** Alta (motivo número 1 de descarte imediato).
- **Impacto:** Sinaliza falta de atenção a detalhes, desleixo na revisão e baixa capacidade de comunicação escrita.
- **Atenção especial:** Nomes de tecnologias (escrever "Phyton", "Javacript", "Github", "Fast Api" em vez de *Python*, *JavaScript*, *GitHub*, *FastAPI* causa péssima impressão técnica).

### 2. Currículo Genérico "Tamanho Único"
- **Gravidade:** Alta.
- **Impacto:** Enviar o mesmo currículo genérico para uma vaga de Engenharia de Dados e para uma vaga de Desenvolvimento Web Frontend. O recrutador percebe em segundos que o candidato não leu a descrição da vaga.
- **Solução:** O objetivo profissional, a ordem das tecnologias e os projetos em destaque devem ser ajustados para a vaga específica.

### 3. Falta de Contexto ou Bullets Passivos
- **Gravidade:** Média-Alta.
- **Impacto:** Bullets como *"Ajudava na manutenção do banco"* ou *"Fazia reuniões semanais"*. Não comunicam o que foi aprendido, que tecnologia foi usada nem qual foi o resultado atingido.

### 4. Links Inacessíveis ou Quebrados
- **Gravidade:** Média-Alta.
- **Impacto:** O recrutador clica no link do GitHub ou do Portfólio e encontra erro 404, repositório vazio com apenas um arquivo README sem código, ou perfil do LinkedIn desatualizado.
- **Regra:** Se incluir link para projeto, certifique-se de que o repositório possua código organizado, documentação e instruções claras de execução.

### 5. Inclusão de Informações Pessoais Desnecessárias
- **Gravidade:** Média.
- **Impacto:** Polui visualmente o currículo e ocupa espaço precioso de uma única página.
- **Nunca incluir:**
  - Foto (salvo exigência expressa da vaga, raríssimo em tech).
  - Número de CPF, RG, CNH, título de eleitor.
  - Endereço físico completo com rua e número do apartamento (basta Cidade/UF).
  - Pretensão salarial (assunto para a etapa de entrevista).
  - Nome de pais ou referências pessoais não solicitadas.

### 6. Alucinação de Habilidades (Overclaiming)
- **Gravidade:** Crítica.
- **Impacto:** Listar uma tecnologia que o estudante apenas "ouviu falar" ou assistiu um vídeo de 15 minutos. Se for chamado para a entrevista técnica e não souber explicar o básico, o candidato é desqualificado e perde a credibilidade com a empresa.
- **Regra RAG:** O gerador de currículo deve utilizar **apenas** competências e dados presentes no perfil real do candidato (`candidate_profile.yaml`).

---

## 3. Checklist de Validação Final Antes do Envio
- [ ] O currículo cabe exatamente em 1 página PDF sem transbordar.
- [ ] Não há nenhum erro de grafia em termos técnicos, nomes de bibliotecas ou gramática.
- [ ] Todos os links (LinkedIn, GitHub, projetos) funcionam e abrem nas páginas corretas.
- [ ] O objetivo profissional cita especificamente a oportunidade e a área pretendida.
- [ ] As 3 habilidades mais exigidas na vaga estão comprovadas na prática em projetos ou experiências.
