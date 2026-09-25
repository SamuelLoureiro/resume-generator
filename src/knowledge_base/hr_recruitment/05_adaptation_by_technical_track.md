# Resume Adaptation Strategies by Technical Track

## 1. The Thematic Fit Principle
The RAG pipeline must identify the **predominant technical track** of the job posting and calibrate the emphasis of resume sections to foreground the competencies most relevant to the target role.

---

## 2. Guidelines by Specialty Track

### Track 1: Artificial Intelligence, LLMs, and RAG Engineering
- **What recruiters in this area prioritize:**
  - Practical experience with LLM orchestration frameworks (`LlamaIndex`, `LangChain`).
  - Knowledge of vector databases (`ChromaDB`, `Pinecone`, `FAISS`, `Qdrant`).
  - Language model evaluation (metrics from the `RAGAS` framework: accuracy, hallucination rate, relevance).
  - Hybrid search strategies (dense Embeddings + BM25) and text chunking.
  - Structured prompt engineering and function calling.
- **How to adapt the resume:**
  - The professional objective must explicitly mention interest in Generative AI and RAG.
  - The Resume RAG Generator project should be the first featured item in the projects section.
  - In the skills section, place *LlamaIndex*, *Google Gemini*, *ChromaDB*, and *PyTorch* at the top.

### Track 2: Data Science and Data Engineering
- **What recruiters in this area prioritize:**
  - Absolute fluency in Python and SQL for relational and analytical data manipulation and querying.
  - Processing libraries: `Pandas`, `NumPy`, `Polars`, `Scikit-Learn`.
  - Building ETL (Extract, Transform, Load) pipelines.
  - Data cleaning, handling missing values, and Exploratory Data Analysis (EDA).
  - Creating dashboards or reports for decision-making.
- **How to adapt the resume:**
  - Emphasize the volume of data processed in each experience or project (e.g., *50,000 records*).
  - Highlight databases used (`PostgreSQL`, `SQLite`, `BigQuery`).
  - Foreground precision, recall, F1 metrics, and data visualization.

### Track 3: Software Engineering and Backend Development
- **What recruiters in this area prioritize:**
  - Building and consuming structured RESTful APIs (`FastAPI`, `Flask`, or `Django`).
  - Relational database modeling and integration with ORM (`SQLAlchemy`, `PostgreSQL`).
  - Best practices: static typing with Pydantic, automated tests (`pytest`), error handling and exceptions.
  - Basic containerization with Docker and professional version control with Git/GitHub.
- **How to adapt the resume:**
  - Highlight layered architecture of projects, test coverage, and modularity.
  - Emphasize ability to build stable, well-documented systems.

---

## 3. Directive for the LLM Synthesis in the RAG Pipeline
When a job description is provided by the user:
1. The system must extract the core competencies of the posting (e.g., "internship focused on AI").
2. Filter from the candidate's profile (`candidate_profile.yaml`) the projects and achievements with the greatest semantic overlap.
3. Position the technical terms from the job description in the first bullet points of projects and experiences, ensuring that all generated data is truthful and grounded.
