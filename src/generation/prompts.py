"""System prompts and prompt builders for resume generation."""

from __future__ import annotations

import json
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume

SYSTEM_PROMPT = """You are an elite Senior Technical Recruiter and Career Strategist specializing in competitive software engineering, machine learning, and data internship recruitment at top tech companies and high-growth startups.

Your mission is to craft a strictly tailored, ATS-compliant, one-page resume for a student candidate applying for a specific internship role.

### The Five Inviolable Mandates:

1. ABSOLUTE TRUTHFULNESS & ZERO HALLUCINATION (CRITICAL):
   - You MUST ONLY use factual details, experiences, dates, institutions, projects, metrics, and technologies explicitly present in the provided Candidate Profile.
   - NEVER invent, assume, inflate, or extrapolate experiences, companies, degrees, grades, project names, or skills that the candidate did not report.
   - Any hallucinated credential will cause immediate disqualification in technical interviews.
   - If the candidate lacks a specific qualification requested in the job, highlight their closest related real competency and solid foundational coursework instead of fabricating claims.

2. THE GOOGLE XYZ ACHIEVEMENT FORMULA:
   - For all bullet points in Experience and Projects, frame achievements using Google's formula:
     "Accomplished [X] as measured by [Y], by doing [Z]"
   - Quantify results wherever technical metrics exist (e.g., latency reduction, test coverage, model accuracy/F1, dataset scale, response time).

3. HIGH-IMPACT ACTION VERBS:
   - Start EVERY bullet point with a vigorous, domain-specific active verb in the past tense (e.g., "Architected", "Engineered", "Implemented", "Optimized", "Benchmarked", "Containerized").
   - Eliminate weak, passive phrases like "Assisted with", "Responsible for", or "Worked on".

4. CONTEXTUAL ATS & KEYWORD ALIGNMENT:
   - Integrate the explicit technologies, frameworks, and requirements from the job description naturally into the bullet points and skills categories.
   - Prioritize candidate skills and projects that have the strongest technical overlap with the job posting.

5. STRICT JSON OUTPUT COMPLIANCE:
   - Your response MUST be a single, valid JSON object strictly adhering to the TailoredResume schema.
   - Do NOT wrap in markdown code blocks if structured output is requested directly, and provide NO introductory or concluding commentary."""


def get_resume_schema_description() -> str:
    """Return JSON schema description of the TailoredResume model."""
    schema = TailoredResume.model_json_schema()
    return json.dumps(schema, indent=2)


def build_resume_generation_prompt(
    candidate: CandidateProfile,
    job: JobPosting,
    retrieved_guidelines: str = "",
) -> str:
    """Build the comprehensive prompt for generating a tailored resume.

    Combines candidate facts, job requirements, RAG knowledge guidelines,
    and schema constraints into a complete LLM user prompt.

    Args:
        candidate: CandidateProfile containing all verified personal and technical data.
        job: JobPosting instance with title, company, requirements, and tech stack.
        retrieved_guidelines: RAG-retrieved recruitment guidelines and best practices.

    Returns:
        str: Fully formatted prompt string for the LLM.
    """
    candidate_data = candidate.model_dump(exclude_none=True)
    candidate_json = json.dumps(candidate_data, indent=2, ensure_ascii=False)

    guidelines_section = ""
    if retrieved_guidelines.strip():
        guidelines_section = f"""
## RAG Knowledge Base Guidelines (Specialized Recruitment Insights)
The following verified guidelines were retrieved specifically for this job application. You MUST apply these recommendations when shaping the resume:

{retrieved_guidelines.strip()}
"""

    prompt = f"""Generate a tailored resume in structured JSON format for the candidate applying to the specified internship role.

## Target Job Posting Details
{job.to_prompt_context()}
{guidelines_section}
## Candidate Verified Profile (Source of Truth)
Below is the candidate's complete, verified background. You MUST draw all resume entries exclusively from this data:

```json
{candidate_json}
```

## Generation Instructions & Required JSON Schema
Your output MUST be a single, valid JSON object matching the following structure:

```json
{{
  "target_job_title": "{job.title}",
  "target_company": "{job.company}",
  "header": {{
    "full_name": "Full Name from candidate profile",
    "email": "Email",
    "phone": "Phone",
    "location": "Location",
    "linkedin_url": "LinkedIn or null",
    "github_url": "GitHub or null"
  }},
  "objective_or_summary": "Concise 2-3 sentence tailored objective specifically mentioning {job.company}.",
  "education": [
    {{
      "institution": "University name",
      "degree": "Degree name",
      "period": "MM/YYYY - MM/YYYY",
      "location": "City/State or null",
      "highlights": ["Honors, GPA, or relevant courses"]
    }}
  ],
  "experiences": [
    {{
      "title": "Role title",
      "organization": "Company or Lab name",
      "period": "MM/YYYY - Present",
      "location": "City/State or Remote",
      "bullets": [
        "Accomplished [X] as measured by [Y], by doing [Z] using active verbs."
      ],
      "technologies": ["Relevant tech from profile"]
    }}
  ],
  "projects": [
    {{
      "name": "Project name from profile",
      "technologies": ["Tech from profile"],
      "url": "URL or null",
      "bullets": [
        "Action bullets demonstrating implementation and quantitative impact."
      ]
    }}
  ],
  "skills": [
    {{
      "category_name": "Programming Languages",
      "skills": ["Python", "SQL"]
    }},
    {{
      "category_name": "Frameworks & Libraries",
      "skills": ["LlamaIndex", "FastAPI"]
    }}
  ],
  "languages": [
    {{
      "language": "Portuguese",
      "proficiency": "Native"
    }}
  ],
  "certifications": [
    "Certification Name (Issuer, MM/YYYY)"
  ]
}}
```

Important rules:
- NEVER invent experiences or qualifications not in the Candidate Verified Profile.
- Use exact keys: "header" (not "contact"), "objective_or_summary", "period" (not start/end dates), and "skills" as a list of categorized skill objects.
- Output ONLY the JSON object strictly matching the TailoredResume schema without markdown fences or additional text."""

    return prompt
