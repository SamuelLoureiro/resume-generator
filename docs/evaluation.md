# 📊 RAG Pipeline Evaluation Report

**Samples evaluated:** 5  
**Successful:** 5  
**Failed:** 0

---

## Metric Scores

| # | Job Title | Company | Faithfulness ↑ | Answer Relevancy ↑ | Context Precision ↑ | Aggregate ↑ |
|---|-----------|---------|:--------------:|:------------------:|:-------------------:|:-----------:|
| 1 | Estágio em Inteligência Artificial & Engenharia de IA (GenAI / RAG) | NeuralWave Labs | 1.000 | 1.000 | 1.000 | 1.000 ✅ |
| 2 | Estágio em Ciência de Dados e Machine Learning | FinMetrics Analytics | 1.000 | 1.000 | 0.750 | 0.909 ✅ |
| 3 | Estágio em Desenvolvimento Backend Python | CloudScale Software | 1.000 | 1.000 | 0.875 | 0.956 ✅ |
| 4 | Estágio em Engenharia de Software (Fundamentals & Systems) | Apex Global Tech | 1.000 | 1.000 | 0.625 | 0.855 ✅ |
| 5 | Estágio em Engenharia de Dados | OmniData Solutions | 1.000 | 1.000 | 0.375 | 0.721 ✅ |

> **Averages (n=5):** Faithfulness `1.000` | Answer Relevancy `1.000` | Context Precision `0.725` | Aggregate `0.898`

## 📝 Qualitative Evaluator Feedback

### 1. Estágio em Inteligência Artificial & Engenharia de IA (GenAI / RAG) @ NeuralWave Labs
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the retrieved context against the user's query, let's break it down using the specified criteria:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Feedback:** Yes, the retrieved context strongly matches the subject matter. The query is about an internship job in Artificial Intelligence & AI Engineering focusing on Generative AI, RAG, and specific technologies (Python, LlamaIndex, Google Gemini, ChromaDB, PyTorch). The context includes explicit guidelines for "Track 1: Artificial Intelligence, LLMs, and RAG Engineering," which covers orchestrators like `LlamaIndex`, vector databases like `ChromaDB`, and resume adaptation strategies matching these exact requirements. 
   - **Score:** 2/2

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Feedback:** The retrieved context provides comprehensive guidelines, resume adaptation strategies, and formatting rules specifically tailored for AI/RAG engineering roles (Track 1). It directly addresses how to align skills like *LlamaIndex*, *Google Gemini*, *ChromaDB*, and *PyTorch* for an AI internship role. However, because it is a set of guidelines and templates rather than a direct answer to a specific question (the user only provided a job title, technologies, and keywords without a direct question), it serves as the underlying framework/instructions rather than a direct informational answer. Nonetheless, it contains all the necessary domain-specific knowledge to formulate the requested resume adaptation.
   - **Score:** 2/2

[RESULT] 4.0

### 2. Estágio em Ciência de Dados e Machine Learning @ FinMetrics Analytics
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate if the retrieved context is relevant to the user's query, let's analyze it based on the specified criteria questions:

1. **Does the retrieved context match the subject matter of the user's query?**
   * **Score:** 2/2
   * **Feedback:** The user's query specifies a job title ("Estágio em Ciência de Dados e Machine Learning at FinMetrics Analytics"), required technologies (Python, Scikit-Learn, Pandas, NumPy, PyTorch, SQL, Git), and keywords. The retrieved context directly addresses resume adaptation strategies for data science and machine learning roles, ATS keyword matching, structuring projects, and what recruiters look for in technical internships. There is a strong thematic match.

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   * **Score:** 1/2
   * **Feedback:** While the retrieved context provides extremely useful guidelines on *how* to build, adapt, and optimize a resume for a Data Science and Machine Learning internship (covering structural guidelines, Track 2 Data Science priorities, keyword matching, and soft skills), it does not actually *generate* or write the specific resume tailored for the "FinMetrics Analytics" position using the provided technologies. It provides the framework and rules, but an additional step or specific resume content generation would be needed to fully answer the implied request. 

[RESULT] 3.0

### 3. Estágio em Desenvolvimento Backend Python @ CloudScale Software
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the retrieved context against the user's query, let's break it down step-by-step:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Score:** 2/2
   - **Feedback:** The retrieved context directly aligns with the subject matter of the user's query. The query specifies a backend development internship role focusing on Python, FastAPI, PostgreSQL, Docker, Git, and Linux. The context explicitly features "Track 3: Software Engineering and Backend Development," which details recruiter priorities for building RESTful APIs with FastAPI, relational database modeling with PostgreSQL, containerization with Docker, and version control with Git/GitHub. 

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Score:** 1.5/2
   - **Feedback:** The context provides extremely relevant guidelines on how to tailor a resume, prioritize technical terms, structure projects, and frame experiences using the exact technologies mentioned in the query (Python, FastAPI, PostgreSQL, Docker, Git). However, because it is a general framework/instructional guide for resume building and RAG pipeline synthesis rather than a direct company-specific answer for "CloudScale Software," it serves as the foundational material to generate the answer rather than being the final standalone response itself. 

[RESULT] 3.5

### 4. Estágio em Engenharia de Software (Fundamentals & Systems) @ Apex Global Tech
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the relevance of the retrieved context against the user's query, let's break down the criteria step-by-step:

1. **Does the retrieved context match the subject matter of the user's query?**
   * **Score:** 2/2
   * **Feedback:** The query specifies a job role ("Estágio em Engenharia de Software (Fundamentals & Systems) at Apex Global Tech") alongside required technologies (Python, C/C++, Estruturas de Dados, Algoritmos, Git, Linux) and keywords. The retrieved context contains specific guidelines for Software Engineering and Backend Development tracks, instructions on how to handle RAG pipeline synthesis for job descriptions, and general resume optimization rules for technical roles. Thus, the subject matter strongly matches the domain of software engineering internships and resume tailoring.

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   * **Score:** 0.5/2
   * **Feedback:** While the retrieved context provides valuable guidelines on *how* to build a resume, format it for ATS, and structure software engineering sections, it does not actually *generate* or *provide* the finalized tailored resume content for the specific job ("Apex Global Tech") or integrate all specific technologies mentioned (such as C/C++, Linux, or specific data structures) into a ready-to-use output. It acts more like system instructions or guidelines rather than the direct answer to the prompt's implied generation task.

[RESULT] 2.5

### 5. Estágio em Engenharia de Dados @ OmniData Solutions
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the relevance of the retrieved context to the user's query, let's go through the evaluation criteria step-by-step:

1. **Does the retrieved context match the subject matter of the user's query?**
   - *Feedback:* The query asks for information regarding an "Estágio em Engenharia de Dados at OmniData Solutions" requiring specific technologies like Python, SQL, PostgreSQL, Docker, Linux, and Git. The retrieved context contains guidelines for resume tailoring, ATS checklists, RAG synthesis directives, backend development tracks mentioning PostgreSQL and Docker, and soft skills for interns. While it touches on general career advice, resume formatting, and mentions some matching technical keywords (like PostgreSQL and Docker), it does not provide specific contextual information about the actual job role, company (OmniData Solutions), or a tailored plan for this exact data engineering internship query. 
   - *Score:* 1.0 / 2.0

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - *Feedback:* No. The context provides general instructions on how an LLM should synthesize resumes, ATS guidelines, and soft skills advice, but it completely lacks specific data engineering context tailored to the OmniData Solutions internship or a complete mapping of all requested technologies (Python, SQL, Linux, Git) applied to this specific role. It cannot independently answer or fulfill the operational intent behind the prompt without external information.
   - *Score:* 0.5 / 2.0

[RESULT] 1.5


---

## Metric Definitions

| Metric | RAGAS Parallel | Definition |
|--------|---------------|-----------|
| **Faithfulness** | `faithfulness` | Fraction of resume claims grounded in the verified candidate profile. Score 1.0 = zero hallucination. |
| **Answer Relevancy** | `answer_relevancy` | Degree to which the generated resume is relevant for the target job description. |
| **Context Precision** | `context_precision` | Signal-to-noise ratio of the knowledge-base chunks retrieved by the hybrid retriever. |
| **Aggregate** | — | Geometric mean of the three scores. Penalises extreme weakness in any single dimension. |

> *Evaluator backend: LlamaIndex native evaluators (Gemini judge LLM).*  
> *See ADR-009 in `docs/decisions_log.md` for rationale.*
