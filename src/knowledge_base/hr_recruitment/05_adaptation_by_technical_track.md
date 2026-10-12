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

### Track 2: Data Science and Machine Learning
- **What recruiters in this area prioritize:**
  - Fluency in Python for tabular data manipulation, statistical modeling, and EDA.
  - Processing and ML libraries: `Pandas`, `NumPy`, `Scikit-Learn`, `PyTorch`.
  - Supervised and unsupervised modeling, feature engineering, and cross-validation.
  - Evaluation metrics: accuracy, ROC-AUC, precision, recall, F1-Score, confusion matrices.
  - Data storytelling and visualization (`Matplotlib`, `Seaborn`).
- **How to adapt the resume:**
  - Emphasize projects with real datasets, such as text classification or predictive modeling.
  - Highlight the volume of records analyzed (e.g., *50,000 articles*) and achieved metrics (*88% accuracy*).
  - Prioritize mathematical foundations (Calculus, Linear Algebra, Statistics) and research experience.

### Track 3: Software Engineering and Backend Development
- **What recruiters in this area prioritize:**
  - Building and consuming structured RESTful APIs (`FastAPI`, `Flask`, or `Django`).
  - Relational database modeling and integration with ORM (`SQLAlchemy`, `PostgreSQL`).
  - Software quality: static typing with Pydantic, automated tests (`pytest`), error handling.
  - Containerization with Docker and professional version control with Git/GitHub workflows.
- **How to adapt the resume:**
  - Highlight layered architecture of projects, test coverage, and modularity.
  - Foreground experience in junior enterprises or team software deliveries.
  - Emphasize ability to build stable, well-documented, and tested systems.

### Track 4: Core Software Engineering, Systems, and Algorithms
- **What recruiters in this area prioritize:**
  - Deep command of computer science fundamentals: Data Structures (trees, graphs, heaps, hash tables) and Algorithms.
  - Computational complexity analysis (Big-O notation, time and memory efficiency trade-offs).
  - Proficiency in compiled and systems languages (`C`, `C++`) as well as `Python`.
  - Development and debugging in Unix/Linux terminal environments.
  - Competitive programming (Maratona SBC de Programação, ICPC, OBI, Codeforces).
- **How to adapt the resume:**
  - Emphasize participation and qualification in programming marathons and olympiads.
  - Highlight academic standing (GPA / Coeficiente de Rendimento) and teaching assistantships (Monitoria) in algorithms.
  - Foreground problem-solving velocity, low-level systems understanding, and clean algorithmic code.
  - In technical skills, prioritize `C/C++`, `Python`, `Estruturas de Dados`, `Algoritmos`, `Linux`, and `Git`.

### Track 5: Data Engineering, ETL, and Analytics Infrastructure
- **What recruiters in this area prioritize:**
  - Designing and implementing automated data pipelines and ETL/ELT processes.
  - Advanced SQL: joins, aggregations, window functions, indexing, and schema design.
  - Relational database administration and querying (`PostgreSQL`, `MySQL`).
  - Data ingestion techniques: REST API polling, automated web scraping, structured file formats (CSV, JSON, Parquet).
  - Automation and containerization with `Docker` and Linux shell scripting.
  - Data quality, schema validation, and pipeline observability.
- **How to adapt the resume:**
  - Emphasize data ingestion volumes and pipeline reliability (e.g., *automated scraping and ingestion of 50,000 records*).
  - Foreground database design and query tuning in PostgreSQL.
  - Highlight containerized environments with Docker and Linux workflow automation.
  - Prioritize `SQL`, `Python`, `PostgreSQL`, `Docker`, `Linux`, `ETL/Pipelines` in skills.

### Track 6: Embedded Systems, Automotive ECUs, and Edge AI
- **What recruiters in this area prioritize:**
  - Real-time embedded programming in `C` and `C++` with strict hardware constraint awareness.
  - Real-time operating systems (`FreeRTOS`) and deterministic task scheduling.
  - Automotive protocols and serial buses: `CAN Bus` (distributed ECU networking), `SPI` (master-slave coordination), `I2C` (sensor acquisition), and `UART` (telemetry / PC visualization).
  - Hardware awareness and schematic literacy: collaborating on PCB design and layout requirements (`EasyEDA`), understanding signal integrity and power rails.
  - Edge AI and TinyML deployment: running lightweight neural network inference on microcontrollers (RP2350, STM32, Arduino) under severe memory limits using `Edge Impulse` or quantization.
  - Robotics integration: `ROS 2` communication bridges and state telemetry.
- **How to adapt the resume:**
  - Highlight dual-core or multi-node projects: CAN bus sensor acquisition (STM32, MPU9250) and dual RP2350 data acquisition.
  - Keep communication channel boundaries clear: deterministic SPI inter-device protocol versus UART host PC telemetry.
  - Accurately state PCB involvement as collaborative design assistance (EasyEDA), highlighting hardware awareness without claiming sole senior layout engineering.
  - Foreground TinyML on-device classification metrics (e.g., *80% accuracy in real-time edge classification*).
  - In technical skills, prioritize `C/C++`, `FreeRTOS`, `CAN Bus`, `SPI / I2C / UART`, `STM32`, `Raspberry Pi Pico`, `ROS 2`, `TinyML / Edge Impulse`.

---

## 3. Directive for the LLM Synthesis in the RAG Pipeline
When a job description is provided by the user:
1. The system must extract the core competencies of the posting (e.g., "internship focused on AI").
2. Filter from the candidate's profile (`candidate_profile.yaml`) the projects and achievements with the greatest semantic overlap.
3. Position the technical terms from the job description in the first bullet points of projects and experiences, ensuring that all generated data is truthful and grounded.
