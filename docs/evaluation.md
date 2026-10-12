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
| 3 | Estágio em Desenvolvimento Backend Python | CloudScale Software | 1.000 | 1.000 | 0.750 | 0.909 ✅ |
| 4 | Estágio em Engenharia de Software (Fundamentals & Systems) | Apex Global Tech | 1.000 | 1.000 | 1.000 | 1.000 ✅ |
| 5 | Estágio em Engenharia de Dados | OmniData Solutions | 1.000 | 1.000 | 1.000 | 1.000 ✅ |

> **Averages (n=5):** Faithfulness `1.000` | Answer Relevancy `1.000` | Context Precision `0.900` | Aggregate `0.965`

## 📝 Qualitative Evaluator Feedback

### 1. Estágio em Inteligência Artificial & Engenharia de IA (GenAI / RAG) @ NeuralWave Labs
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the retrieved context against the user's query, let's break down the analysis using the provided criteria questions:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Score:** 2/2
   - **Feedback:** The user's query is about an internship in Artificial Intelligence & AI Engineering focusing on Generative AI and RAG, utilizing specific technologies like Python, LlamaIndex, Google Gemini, ChromaDB, and PyTorch. The retrieved context contains a dedicated section titled "Track 1: Artificial Intelligence, LLMs, and RAG Engineering," which directly addresses the exact technologies, frameworks (LlamaIndex), vector databases (ChromaDB), and resume adaptation guidelines requested in the query.

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Score:** 2/2
   - **Feedback:** Yes, the retrieved context provides comprehensive instructions on how to structure a resume for this exact technical track. It outlines what recruiters prioritize (LLM orchestration, vector databases) and gives precise instructions on how to adapt the resume (e.g., placing *LlamaIndex*, *Google Gemini*, *ChromaDB*, and *PyTorch* at the top of the skills section, mentioning Generative AI and RAG in the professional objective, and featuring relevant projects). This is fully sufficient to guide the synthesis for the given query.

[RESULT] 4.0

### 2. Estágio em Ciência de Dados e Machine Learning @ FinMetrics Analytics
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the relevance of the retrieved context to the user's query, let's analyze it step by step based on the provided criteria:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Score: 2/2**
   - **Reasoning:** The user's query is about a job posting for an "Estágio em Ciência de Dados e Machine Learning" (Data Science and Machine Learning Internship) at FinMetrics Analytics, requiring technologies such as Python, Scikit-Learn, Pandas, NumPy, PyTorch, SQL, and Git. The retrieved context contains a specific section ("Track 2: Data Science and Machine Learning") that directly addresses what recruiters in this field prioritize, including Pandas, NumPy, Scikit-Learn, and PyTorch, as well as general technical skills matching the query domain.

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Score: 1/2**
   - **Reasoning:** While the retrieved context provides valuable guidelines on how to adapt a resume for a Data Science and Machine Learning track (highlighting the exact tools mentioned in the query like Pandas, NumPy, Scikit-Learn, and PyTorch), it is part of a broader resume adaptation guide rather than a direct answer addressing the specific job opening at FinMetrics Analytics itself. It offers strategic advice rather than a customized response or full answer to a specific application prompt.

[RESULT] 3.0

### 3. Estágio em Desenvolvimento Backend Python @ CloudScale Software
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the retrieved context against the user's query, let's break down the assessment based on the two provided criteria questions:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Analysis:** The user's query is about a backend development internship position ("Estágio em Desenvolvimento Backend Python at CloudScale Software") focusing on technologies such as Python, FastAPI, PostgreSQL, Docker, Git, and Linux. 
   - The retrieved context contains a dedicated section ("Track 3: Software Engineering and Backend Development") which directly discusses backend priorities such as RESTful APIs (`FastAPI`), relational databases (`PostgreSQL`), containerization (`Docker`), and version control (`Git`), as well as general Linux and Python mentions across other tracks. 
   - **Score:** 2 / 2 (The context strongly aligns with the subject matter of backend software engineering).

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Analysis:** While the context provides highly relevant advice on how to adapt a resume for backend software engineering (mentioning FastAPI, PostgreSQL, Docker, Git, and Python), it is a set of general guidelines and resume-tailoring instructions rather than a direct, self-contained answer to a specific question about the job description itself. It lacks specific contextual details about the "CloudScale Software" company or the exact job description requirements beyond matching general backend skill tracks. Therefore, while it provides excellent supportive material, it cannot exclusively answer a comprehensive prompt about this specific job listing without external information.
   - **Score:** 1 / 2 (Provides good supporting guidelines for the technologies, but lacks specific details answering a direct query about the specific company/role).

[RESULT] 3.0

### 4. Estágio em Engenharia de Software (Fundamentals & Systems) @ Apex Global Tech
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** **Feedback:**

1. **Does the retrieved context match the subject matter of the user's query?**
   Yes, the retrieved context directly matches the subject matter. The user is asking about an internship job ("Estágio em Engenharia de Software (Fundamentals & Systems)") requiring specific technologies and keywords (Python, C/C++, Estruturas de Dados, Algoritmos, Git, Linux). The retrieved context explicitly covers "Core Software Engineering, Systems, and Algorithms Internships" and lists the exact technical skills, languages (C, C++, Python), foundations (Estruturas de Dados, Algoritmos), and tools (Linux, Git) required for this specific track. *(Score: 2/2)*

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   Yes. The context provides comprehensive guidance, ATS keywords, action verbs, and skill prioritizations specifically tailored for a Core Software Engineering and Systems internship. It covers all the requested technologies and maps them directly to how a candidate should position themselves for this exact job description. *(Score: 2/2)*

[RESULT] 4.0

### 5. Estágio em Engenharia de Dados @ OmniData Solutions
- **Faithfulness:** YES
- **Answer Relevancy:** YES
- **Context Precision:** To evaluate the relevance of the retrieved context to the user's query, let's go through the evaluation steps:

1. **Does the retrieved context match the subject matter of the user's query?**
   - **Score: 2/2**
   - **Feedback:** The user's query is about an internship role in Data Engineering ("Estágio em Engenharia de Dados") at OmniData Solutions, requiring specific technologies like Python, SQL, PostgreSQL, Docker, Linux, and Git. The retrieved context directly addresses Data Engineering internships, outlines what recruiters look for in this exact track, lists the exact technical skills (Python, SQL, PostgreSQL, Docker, Linux, Git), provides ATS keywords, and gives specific instructions on how to adapt resumes and synthesize RAG pipelines for this domain. 

2. **Can the retrieved context be used exclusively to provide a full answer to the user's query?**
   - **Score: 2/2**
   - **Feedback:** The retrieved context contains all the necessary guidelines, prioritized technical skills, action verbs, and structural instructions needed to tailor a candidate's profile/resume for a Data Engineering internship using the exact technologies specified in the query. It provides a complete blueprint for addressing the user's job application requirements.

[RESULT] 4.0


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
