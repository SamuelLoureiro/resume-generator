"""Synthetic candidate profiles and atomic facts for evaluation benchmarking.

Provides two ground-truth candidate datasets for testing system behavior
beyond a single candidate (docs/research_plan.md, Section 3.2):
1. Profile A (Fresh Graduate): Strong academic fundamentals, personal projects,
   tutoring/TA experience, zero corporate/industry software internships.
2. Profile B (Academic Researcher): MSc/BSc degrees, research lab publications,
   fellowships, mathematical/ML experiments, zero corporate internships.
"""

from __future__ import annotations

from src.data.candidate import (
    CandidateProfile,
    ContactInfo,
    Education,
    Experience,
    Language,
    Project,
    Skills,
)
from src.data.facts import AtomicFact, CandidateFacts


def get_synthetic_fresh_grad() -> tuple[CandidateProfile, CandidateFacts]:
    """Return Profile A (Fresh Graduate) and its verified atomic facts."""
    profile = CandidateProfile(
        contact=ContactInfo(
            full_name="Alex Rivera",
            email="alex.rivera@example.edu",
            phone="+55 35 98888 1111",
            location="Itajubá, MG - Brazil",
            linkedin_url="https://linkedin.com/in/alex-rivera",
            github_url="https://github.com/alexrivera",
        ),
        summary="Computer Science undergraduate with solid algorithms and systems foundations seeking a software engineering internship.",
        education=[
            Education(
                institution="Federal University of Itajubá",
                degree="Bachelor of Science in Computer Science",
                start_date="03/2023",
                end_date="12/2026",
                current=True,
                gpa_or_honors="Top 5% class ranking",
                relevant_coursework=[
                    "Data Structures",
                    "Design and Analysis of Algorithms",
                    "Operating Systems",
                    "Computer Networks",
                    "Database Management Systems",
                ],
                highlights=[
                    "Selected as Teaching Assistant for Data Structures & Algorithms",
                ],
            )
        ],
        experiences=[
            Experience(
                title="Teaching Assistant - Data Structures & Algorithms",
                organization="Federal University of Itajubá",
                location="Itajubá, Brazil",
                start_date="03/2024",
                end_date="12/2024",
                current=False,
                bullets=[
                    "Conducted weekly lab sessions for 40+ undergraduate students covering trees, graphs, and dynamic programming.",
                    "Developed automated grading test suites in Python and C++ reducing evaluation turnaround time by 60%.",
                ],
                technologies=["Python", "C++", "Git", "Linux"],
            )
        ],
        projects=[
            Project(
                name="Distributed Task Queue",
                description="Lightweight distributed job queue supporting asynchronous execution and exponential backoff retry.",
                bullets=[
                    "Developed a distributed task queue in Python using Redis for broker queueing and worker orchestration.",
                    "Implemented worker pool heartbeat monitoring and task dead-letter queue handling 500 tasks/second.",
                ],
                technologies=["Python", "Redis", "Docker", "PyTest"],
                url="https://github.com/alexrivera/distributed-task-queue",
            ),
            Project(
                name="Disk-Backed B+ Tree Index",
                description="Persistent B+ tree storage engine implementing slotted-page architecture and LRU page buffer cache.",
                bullets=[
                    "Built a disk-backed B+ tree index engine in C++ supporting concurrent point queries and range scans.",
                    "Implemented an LRU page buffer pool managing 4KB storage pages with thread-safe eviction policies.",
                ],
                technologies=["C++", "CMake", "GTest", "Linux"],
                url="https://github.com/alexrivera/btree-engine",
            ),
        ],
        skills=Skills(
            programming_languages=["Python", "C++", "C", "SQL", "Bash"],
            frameworks_and_libraries=["FastAPI", "PyTest", "GTest"],
            databases=["PostgreSQL", "Redis", "SQLite"],
            tools_and_platforms=["Git", "Docker", "Linux", "CMake"],
            soft_skills=[
                "Problem Solving",
                "Technical Communication",
                "Team Collaboration",
                "Analytical Thinking",
            ],
        ),
        languages=[
            Language(language="Portuguese", proficiency="Native"),
            Language(language="English", proficiency="Fluent (C1)"),
        ],
        certifications=[],
        additional_info=[
            "Bronze Medal - Brazilian Intercollegiate Programming Contest (SBC Regional, 2024)",
        ],
    )

    facts = CandidateFacts(
        facts=[
            AtomicFact(
                id="edu_rivera_cs",
                source="education[0]",
                text="Enrolled in B.Sc. in Computer Science at Federal University of Itajubá (03/2023 - 12/2026) with top 5% class ranking.",
                scope_ceiling=1,
                tracks=["core_swe", "backend"],
                priority=1,
                metrics=["Top 5%"],
                tags=["algorithms", "operating-systems", "databases"],
            ),
            AtomicFact(
                id="exp_rivera_ta_teaching",
                source="experiences[0].bullets[0]",
                text="Conducted weekly lab sessions for 40+ undergraduate students covering trees, graphs, and dynamic programming.",
                scope_ceiling=3,
                tracks=["core_swe"],
                priority=2,
                metrics=["40+ undergraduate students"],
                tags=["algorithms", "data-structures", "mentoring"],
            ),
            AtomicFact(
                id="exp_rivera_ta_automation",
                source="experiences[0].bullets[1]",
                text="Developed automated grading test suites in Python and C++ reducing evaluation turnaround time by 60%.",
                scope_ceiling=3,
                tracks=["core_swe", "backend"],
                priority=1,
                metrics=["60%"],
                tags=["python", "c++", "testing", "automation"],
            ),
            AtomicFact(
                id="proj_rivera_queue_dev",
                source="projects[0].bullets[0]",
                text="Developed a distributed task queue in Python using Redis for broker queueing and worker orchestration.",
                scope_ceiling=3,
                tracks=["backend", "core_swe"],
                priority=1,
                metrics=[],
                tags=["python", "redis", "distributed-systems"],
            ),
            AtomicFact(
                id="proj_rivera_queue_perf",
                source="projects[0].bullets[1]",
                text="Implemented worker pool heartbeat monitoring and task dead-letter queue handling 500 tasks/second.",
                scope_ceiling=3,
                tracks=["backend", "core_swe"],
                priority=2,
                metrics=["500 tasks/second"],
                tags=["redis", "concurrency", "monitoring"],
            ),
            AtomicFact(
                id="proj_rivera_btree_dev",
                source="projects[1].bullets[0]",
                text="Built a disk-backed B+ tree index engine in C++ supporting concurrent point queries and range scans.",
                scope_ceiling=3,
                tracks=["core_swe", "backend"],
                priority=1,
                metrics=[],
                tags=["c++", "b-tree", "storage-engine", "indexing"],
            ),
            AtomicFact(
                id="proj_rivera_btree_lru",
                source="projects[1].bullets[1]",
                text="Implemented an LRU page buffer pool managing 4KB storage pages with thread-safe eviction policies.",
                scope_ceiling=3,
                tracks=["core_swe"],
                priority=2,
                metrics=["4KB"],
                tags=["c++", "memory-management", "lru", "concurrency"],
            ),
        ]
    )

    return profile, facts


def get_synthetic_researcher() -> tuple[CandidateProfile, CandidateFacts]:
    """Return Profile B (Academic Researcher) and its verified atomic facts."""
    profile = CandidateProfile(
        contact=ContactInfo(
            full_name="Elena Rostova",
            email="elena.rostova@example.univ.fr",
            phone="+33 7 99 88 77 66",
            location="Grenoble, France",
            linkedin_url="https://linkedin.com/in/elena-rostova",
            github_url="https://github.com/erostova",
        ),
        summary="MSc student in Artificial Intelligence specializing in Graph Neural Networks and NLP looking for an applied research internship.",
        education=[
            Education(
                institution="Grenoble Institute of Technology (Grenoble INP)",
                degree="Master of Science in Artificial Intelligence",
                start_date="09/2023",
                end_date="06/2025",
                current=True,
                gpa_or_honors="Excellence Scholarship Recipient",
                relevant_coursework=[
                    "Deep Learning",
                    "Graph Representation Learning",
                    "Natural Language Processing",
                    "Statistical Machine Learning",
                ],
                highlights=[
                    "Author of workshop paper on Graph Neural Operators at NeurIPS workshop",
                ],
            ),
            Education(
                institution="University of Campinas (UNICAMP)",
                degree="Bachelor of Science in Applied Mathematics",
                start_date="03/2019",
                end_date="12/2022",
                current=False,
                gpa_or_honors="Graduated Summa Cum Laude",
                relevant_coursework=[
                    "Linear Algebra",
                    "Multivariate Calculus",
                    "Probability and Statistics",
                    "Numerical Analysis",
                ],
            ),
        ],
        experiences=[
            Experience(
                title="Graduate Research Assistant",
                organization="LIG Computer Science Laboratory",
                location="Grenoble, France",
                start_date="10/2023",
                end_date="Present",
                current=True,
                bullets=[
                    "Investigated equivariant Graph Neural Networks for molecular property prediction in PyTorch Geometric.",
                    "Designed graph spectral pooling layers improving MAE by 14% on QM9 regression benchmarks.",
                ],
                technologies=["Python", "PyTorch", "PyTorch Geometric", "Weights & Biases", "Slurm"],
            ),
            Experience(
                title="Scientific Initiation Fellow (PIBIC / CNPq)",
                organization="Institute of Mathematics (UNICAMP)",
                location="Campinas, Brazil",
                start_date="08/2021",
                end_date="07/2022",
                current=False,
                bullets=[
                    "Formulated non-convex optimization algorithms for spectral clustering on large-scale sparse matrices.",
                    "Implemented vectorized numerical solvers in Python and SciPy accelerating matrix decomposition by 3x.",
                ],
                technologies=["Python", "NumPy", "SciPy", "Matplotlib"],
            ),
        ],
        projects=[
            Project(
                name="Low-Resource Machine Translation",
                description="Transfer learning framework fine-tuning mBART-50 for low-resource Romance languages.",
                bullets=[
                    "Fine-tuned mBART-50 encoder-decoder models on French-Occitan parallel corpora using HuggingFace Transformers.",
                    "Achieved 28.4 BLEU score, surpassing standard bilingual transformer baselines by 4.2 points.",
                ],
                technologies=["PyTorch", "HuggingFace", "Transformers", "CUDA"],
                url="https://github.com/erostova/low-resource-nmt",
            )
        ],
        skills=Skills(
            programming_languages=["Python", "R", "C", "LaTeX", "SQL"],
            frameworks_and_libraries=[
                "PyTorch",
                "PyTorch Geometric",
                "HuggingFace",
                "Scikit-Learn",
                "NumPy",
                "SciPy",
            ],
            databases=["SQLite", "PostgreSQL"],
            tools_and_platforms=["Git", "Linux", "Slurm", "Weights & Biases", "Docker"],
            soft_skills=[
                "Mathematical Rigor",
                "Scientific Writing",
                "Experimental Design",
                "Cross-Disciplinary Collaboration",
            ],
        ),
        languages=[
            Language(language="Portuguese", proficiency="Native"),
            Language(language="English", proficiency="Fluent (C2)"),
            Language(language="French", proficiency="Advanced (B2)"),
        ],
        certifications=[],
        additional_info=[
            "Co-author of paper: 'Spectral Invariants in Graph Neural Operators', NeurIPS Workshop (2024)",
        ],
    )

    facts = CandidateFacts(
        facts=[
            AtomicFact(
                id="edu_rostova_msc",
                source="education[0]",
                text="Enrolled in MSc in Artificial Intelligence at Grenoble Institute of Technology (09/2023 - 06/2025).",
                scope_ceiling=1,
                tracks=["ai", "data"],
                priority=1,
                metrics=[],
                tags=["deep-learning", "graph-neural-networks", "nlp"],
            ),
            AtomicFact(
                id="exp_rostova_gnn_research",
                source="experiences[0].bullets[0]",
                text="Investigated equivariant Graph Neural Networks for molecular property prediction in PyTorch Geometric.",
                scope_ceiling=3,
                tracks=["ai", "data"],
                priority=1,
                metrics=[],
                tags=["pytorch", "pytorch-geometric", "graph-neural-networks"],
            ),
            AtomicFact(
                id="exp_rostova_spectral_pooling",
                source="experiences[0].bullets[1]",
                text="Designed graph spectral pooling layers improving MAE by 14% on QM9 regression benchmarks.",
                scope_ceiling=3,
                tracks=["ai", "data"],
                priority=1,
                metrics=["14%"],
                tags=["gnn", "deep-learning", "benchmarking"],
            ),
            AtomicFact(
                id="exp_rostova_pibic_opt",
                source="experiences[1].bullets[0]",
                text="Formulated non-convex optimization algorithms for spectral clustering on large-scale sparse matrices.",
                scope_ceiling=3,
                tracks=["data", "ai"],
                priority=2,
                metrics=[],
                tags=["optimization", "linear-algebra", "clustering"],
            ),
            AtomicFact(
                id="exp_rostova_pibic_scipy",
                source="experiences[1].bullets[1]",
                text="Implemented vectorized numerical solvers in Python and SciPy accelerating matrix decomposition by 3x.",
                scope_ceiling=3,
                tracks=["data", "ai", "core_swe"],
                priority=1,
                metrics=["3x"],
                tags=["python", "scipy", "optimization"],
            ),
            AtomicFact(
                id="proj_rostova_nmt_finetune",
                source="projects[0].bullets[0]",
                text="Fine-tuned mBART-50 encoder-decoder models on French-Occitan parallel corpora using HuggingFace Transformers.",
                scope_ceiling=3,
                tracks=["ai"],
                priority=1,
                metrics=[],
                tags=["huggingface", "transformers", "nlp", "transfer-learning"],
            ),
            AtomicFact(
                id="proj_rostova_nmt_bleu",
                source="projects[0].bullets[1]",
                text="Achieved 28.4 BLEU score, surpassing standard bilingual transformer baselines by 4.2 points.",
                scope_ceiling=3,
                tracks=["ai"],
                priority=1,
                metrics=["28.4 BLEU", "4.2 points"],
                tags=["nlp", "bleu", "evaluation"],
            ),
        ]
    )

    return profile, facts
