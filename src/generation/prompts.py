"""System prompts and prompt builders for resume generation."""

from __future__ import annotations

import json
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume

SYSTEM_PROMPT = """You are an elite Senior Technical Recruiter and Career Strategist specializing in competitive software engineering, machine learning, and data internship recruitment at top tech companies and high-growth startups.

Your mission is to craft a strictly tailored, ATS-compliant, one-page resume for a student candidate applying for a specific internship role.

### The Inviolable Mandates:

1. ABSOLUTE TRUTHFULNESS & ZERO HALLUCINATION (CRITICAL):
   - You MUST ONLY use factual details, experiences, dates, institutions, projects, metrics, and technologies explicitly present in the provided Candidate Profile.
   - NEVER invent, assume, inflate, or extrapolate experiences, companies, degrees, grades, project names, or skills that the candidate did not report.
   - Any hallucinated credential will cause immediate disqualification in technical interviews.
   - If the candidate lacks a specific qualification requested in the job, highlight their closest related real competency and solid foundational coursework instead of fabricating claims.
   - GROUNDING FIRST & PRESERVE TECHNICAL FORMULATIONS: When a candidate's bullet point is already technically accurate and concrete, PRESERVE the candidate's exact technical terminology, device roles, and protocol destinations (e.g., do NOT merge or conflate distinct protocols, and do NOT insert ungrounded marketing adjectives like 'robust' or replace plain data terms like 'movement data' with corporate buzzwords).
   - ATOMIC FACT ISOLATION (NO FACT FUSION): Never combine two facts in one sentence. A scope noun (team, department, area) must stay attached to the fact it came from.
   - CANDIDATE GROUNDED PHRASING (NO JOB PHRASE ECHO): Do not copy phrases from the job posting. Use the candidate's own wording from the facts.
   - RECRUITER-FACING COPY (NO PIPELINE VOCABULARY): Never mention verification, facts, or the generation process.
   - RELEVANCE ALIGNMENT: Prefer facts whose tracks match the job track; for coursework, include only courses that map to at least one job keyword.

2. THE GOOGLE XYZ ACHIEVEMENT FORMULA:
   - For all bullet points in Experience and Projects, frame achievements using Google's formula:
     "Accomplished [X] as measured by [Y], by doing [Z]"
   - Quantify results wherever technical metrics exist (e.g., latency reduction, test coverage, model accuracy/F1, dataset scale, response time).

3. HIGH-IMPACT ACTION VERBS:
   - Start EVERY bullet point with a vigorous, domain-specific active verb in the past tense (e.g., "Architected", "Engineered", "Implemented", "Optimized", "Benchmarked", "Containerized" / in French: "Développé", "Conçu", "Optimisé", "Déployé" / in Portuguese: "Desenvolveu", "Implementou", "Otimizou").
   - Eliminate weak, passive phrases like "Assisted with", "Responsible for", or "Worked on".

4. CONTEXTUAL ATS & KEYWORD ALIGNMENT:
   - Integrate the explicit technologies, frameworks, and requirements from the job description naturally into the bullet points and skills categories.
   - Prioritize candidate skills and projects that have the strongest technical overlap with the job posting.

5. STRICT TARGET LANGUAGE CONSISTENCY (NO LANGUAGE MIXING):
   - You MUST generate ALL textual content (objective/summary, experience bullets, project bullets, skill category headings, coursework/honors, and language names) strictly in the target language requested (Portuguese, English, or French).
   - NEVER mix languages. Every section title and body description must be natively and professionally phrased in the target language.

6. STRICT ONE-PAGE CONTENT BUDGET (NEVER EXCEED 1 PAGE):
   - The compiled resume must fit entirely on a single A4 page. Respect these strict limits:
     * Objective/Summary: Maximum 2 to 3 concise lines formulated as a Technical Value Proposition (academic background + core verified technical pillars relevant to the target job + target engineering domain). NEVER write passive cover-letter statements (e.g., 'applying for the internship to contribute to').
     * Experience: Maximum 2-3 high-impact bullets per role.
     * Projects: Select ONLY the top 2-3 most relevant projects. Maximum 2 bullets per project.
     * Education: Maximum 1 concise line of relevant coursework or honors per degree when the candidate has 2 or more degrees.
     * Skills: Group into 3-4 compact, well-defined categories.

7. STRICT JSON OUTPUT COMPLIANCE:
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
    language: str = "pt",
) -> str:
    """Build the comprehensive prompt for generating a tailored resume.

    Combines candidate facts, job requirements, RAG knowledge guidelines,
    language mandate, and schema constraints into a complete LLM user prompt.

    Args:
        candidate: CandidateProfile containing all verified personal and technical data.
        job: JobPosting instance with title, company, requirements, and tech stack.
        retrieved_guidelines: RAG-retrieved recruitment guidelines and best practices.
        language: Target document language ('pt', 'en', or 'fr').

    Returns:
        str: Fully formatted prompt string for the LLM.
    """
    candidate_data = candidate.model_dump(exclude_none=True)
    # SEC-01: Strip personal contact data (email, phone, links, location) to prevent sending PII to external LLM
    candidate_data.pop("contact", None)
    # Phase C: Pre-filter coursework so LLM receives only relevant courses for target job
    from src.verification.text_utils import select_relevant_coursework
    for edu in candidate_data.get("education", []):
        if "relevant_coursework" in edu and edu["relevant_coursework"]:
            edu["relevant_coursework"] = select_relevant_coursework(
                edu["relevant_coursework"], job, max_courses=4
            )
    candidate_json = json.dumps(candidate_data, indent=2, ensure_ascii=False)

    language_directives = {
        "pt": (
            "## Mandato de Idioma: Português (PT-BR)\n"
            "GERE 100% DO CONTEÚDO EM PORTUGUÊS.\n"
            "- Resumo/Objetivo profissional em português.\n"
            "- Bullet points de experiências e projetos em português com verbos de ação fortes no pretérito.\n"
            "- Nomes de categorias de habilidades em português (ex: 'Linguagens de Programação', 'Frameworks e Bibliotecas', 'Ferramentas e Plataformas').\n"
            "- Disciplinas e destaques de educação em português."
        ),
        "en": (
            "## Target Language Mandate: English (EN)\n"
            "GENERATE 100% OF THE CONTENT IN ENGLISH.\n"
            "- Professional summary in English.\n"
            "- Experience and project bullet points in English with strong past-tense action verbs.\n"
            "- Skill category names in English (e.g., 'Programming Languages', 'Frameworks & Libraries', 'Developer Tools & Platforms').\n"
            "- Coursework and academic highlights in English."
        ),
        "fr": (
            "## Consigne de Langue Impérative: Français (FR)\n"
            "GÉNÉREZ 100% DU CONTENU EN FRANÇAIS PROFESSIONNEL.\n"
            "- Résumé/Profil professionnel en français.\n"
            "- Puces d'expériences et de projets en français avec verbes d'action au passé composé/participe (ex: 'Développé', 'Conçu', 'Implémenté', 'Optimisé').\n"
            "- Titres des catégories de compétences en français (ex: 'Langages de programmation', 'Frameworks et bibliothèques', 'Outils et plateformes', 'Bases de données').\n"
            "- Matières et mentions académiques en français."
        ),
    }
    lang_directive = language_directives.get(language, language_directives["pt"])

    if retrieved_guidelines.strip():
        guidelines_section = f"""
## RAG Knowledge Base Guidelines (Specialized Recruitment Insights)
The following verified guidelines were retrieved specifically for this job application. You MUST apply these recommendations when shaping the resume:

{retrieved_guidelines.strip()}
"""
    else:
        guidelines_section = """
## RAG Knowledge Base Guidelines
No specific external guidelines retrieved. Adhere strictly to general technical resume best practices: focus on measurable achievements, strong active verbs, and clean section prioritization.
"""

    prompt = f"""Generate a tailored resume in structured JSON format for the candidate applying to the specified internship role.

{lang_directive}

## Strict 1-Page Layout Budget (CRITICAL)
The resulting resume MUST fit on a single page:
- Summary/Objective: 2 to 3 lines maximum. Formulate as a direct technical value proposition (academic degree + core verified competencies relevant to the role + target engineering domain), avoiding passive applicant statements.
- Experience: Maximum 2-3 concise bullets per role.
- Projects: Select ONLY the top 2-3 most relevant projects. Maximum 2 bullets per project.
- Education: Maximum 1 concise line of coursework or honors per degree (the candidate has multiple degrees; keep each compact).
- Skills: Group into 3-4 compact categories.

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
  "objective_or_summary": "Tailored objective in target language specifically mentioning {job.company}.",
  "education": [
    {{
      "institution": "University name",
      "degree": "Degree name",
      "period": "MM/YYYY - MM/YYYY",
      "location": "City/State or null",
      "highlights": ["Honors, GPA, or relevant courses in target language"]
    }}
  ],
  "experiences": [
    {{
      "title": "Role title",
      "organization": "Company or Lab name",
      "period": "MM/YYYY - Present",
      "location": "City/State or Remote",
      "bullets": [
        "Action bullets demonstrating measurable impact using XYZ formula in target language."
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
        "Action bullets demonstrating implementation and quantitative impact in target language."
      ]
    }}
  ],
  "skills": [
    {{
      "category_name": "Category name in target language",
      "skills": ["Skill1", "Skill2"]
    }}
  ],
  "languages": [
    {{
      "language": "Language name in target language",
      "proficiency": "Proficiency in target language"
    }}
  ],
  "certifications": [
    "Certification Name (Issuer, MM/YYYY)"
  ]
}}
```

Important rules:
- NEVER invent experiences or qualifications not in the Candidate Verified Profile.
- Do NOT output a "header" or contact section; personal contact details are injected deterministically at render time for privacy.
- ALL text MUST be strictly in the requested target language ('{language}').
- Use exact keys: "objective_or_summary", "period" (not start/end dates), and "skills" as a list of categorized skill objects.
- Output ONLY the JSON object strictly matching the TailoredResume schema without markdown fences or additional text."""

    return prompt


PROMPT_VERSION = "v1_gen_v1.1"
V1_FEEDBACK_PROMPT_VERSION = "v1_feedback_v1.1"


def serialize_resume_for_llm(resume: TailoredResume) -> str:
    """Serialize a TailoredResume to a JSON string for multi-turn regeneration.

    Crucially excludes the `header` (contact details) to guarantee SEC-01 compliance:
    candidate PII is never sent to the LLM during generation or regeneration.

    Args:
        resume: TailoredResume to serialize.

    Returns:
        str: Clean JSON string of the resume without header.
    """
    data = resume.model_dump(exclude_none=True)
    data.pop("header", None)
    return json.dumps(data, indent=2, ensure_ascii=False)


def build_regeneration_feedback_prompt(
    issues: list[Any],
    language: str = "en",
) -> str:
    """Build an error-guided regeneration prompt from a list of verification issues.

    Guides the LLM to fix specific hallucinations, unsupported skills/numbers,
    verb inflations, or date/entity mismatches detected by the verifier and judge.

    Args:
        issues: List of VerificationIssue objects.
        language: Resume language code ('en', 'fr', 'pt').

    Returns:
        str: Structured prompt instructing the LLM to correct the resume.
    """
    if language == "fr":
        intro = (
            "## Rapport de Vérification Factualle (Erreurs Détectées)\n"
            "L'audit automatisé et le vérificateur factuel ont identifié les problèmes suivants "
            "dans votre version précédente du CV. Vous DEVEZ corriger chacune de ces anomalies :\n"
        )
        closing = (
            "\n### Consignes Impératives de Correction :\n"
            "1. Supprimez ou remplacez toute compétence ou métrique non vérifiée par des éléments factuels du profil.\n"
            "2. Ajustez les verbes d'action pour respecter scrupuleusement le plafond d'impact autorisé (niveaux 1 à 4).\n"
            "3. Alignez exactement les dates, intitulés de poste et diplômes avec le profil vérifié.\n"
            "4. Maintenez l'intégralité du texte en français et respectez la contrainte stricte d'une seule page.\n"
            "5. Renvoyez UNIQUEMENT l'objet JSON complet et corrigé respectant le schéma TailoredResume, sans bloc d'en-tête (header).\n"
            "6. Si fusion de faits (FACT_FUSION) : Séparez en deux phrases ou ne conservez qu'un seul fait ; gardez les noms sujets (équipe/département/zone) rattachés au fait d'origine.\n"
            "7. Si écho de l'offre (JOB_PHRASE_ECHO) : Réécrivez avec les termes factuels du candidat ; ne copiez pas les phrases de l'offre.\n"
            "8. Supprimez tout méta-mot interne ('vérifié', 'grounded', 'pipeline') du texte."
        )
    elif language == "pt":
        intro = (
            "## Relatório de Verificação Factual (Erros Detectados)\n"
            "A auditoria automatizada e o verificador factual identificaram os seguintes problemas "
            "no currículo gerado anteriormente. Você DEVE corrigir cada uma dessas falhas:\n"
        )
        closing = (
            "\n### Instruções Obrigatórias de Correção:\n"
            "1. Remova ou substitua qualquer habilidade ou número não fundamentado por dados reais do perfil.\n"
            "2. Ajuste verbos de ação para não ultrapassar o teto de escopo verificado (níveis 1 a 4).\n"
            "3. Sincronize datas, cargos e formações exatamente com o perfil verificado.\n"
            "4. Mantenha 100% do texto no idioma solicitado e respeite o limite estrito de 1 página.\n"
            "5. Retorne APENAS o JSON completo e corrigido segundo o esquema TailoredResume, sem bloco de cabeçalho (header).\n"
            "6. Se houver fusão de fatos (FACT_FUSION): Divida em duas frases ou mantenha apenas um fato; mantenha substantivos de sujeito (time/departamento/área) vinculados ao fato de origem.\n"
            "7. Se houver eco de frases da vaga (JOB_PHRASE_ECHO): Reescreva usando a redação dos fatos verificados do candidato; não copie frases da vaga.\n"
            "8. Remova meta-palavras internas do sistema ('verificado', 'grounded', 'pipeline') de todo o texto."
        )
    else:  # en (default)
        intro = (
            "## Factual Verification Audit Report (Defects Detected)\n"
            "The automated verifier and atomic claim judge identified the following issues "
            "in your previous resume output. You MUST correct each of these defects:\n"
        )
        closing = (
            "\n### Mandatory Correction Instructions:\n"
            "1. Remove or replace unverified skills, tools, or metrics with verified facts from the profile.\n"
            "2. Lower inflated action verbs to comply with the verified scope ceiling (e.g. use 'Contributed to' or 'Developed' instead of 'Architected' or 'Led' where indicated).\n"
            "3. Align dates, job titles, and degrees exactly with the verified candidate profile.\n"
            "4. Maintain strict language consistency and the single-page budget.\n"
            "5. Return ONLY the complete, corrected JSON object conforming to the TailoredResume schema, without contact header.\n"
            "6. If FACT_FUSION is detected: Split into two sentences or keep only one fact; keep subject nouns (team/department/area) attached to the fact they come from.\n"
            "7. If JOB_PHRASE_ECHO is detected: Rewrite using candidate's own verified fact wording; do not copy phrases from the job description.\n"
            "8. If SUMMARY_LINT is detected: Remove internal pipeline meta-words (such as 'verified', 'grounded', 'pipeline') from free text."
        )

    lines: list[str] = [intro]
    for idx, issue in enumerate(issues, start=1):
        loc = getattr(issue, "location", "resume")
        kind = getattr(issue, "kind", "issue")
        text = getattr(issue, "text", "")
        detail = getattr(issue, "detail", "")
        scope = getattr(issue, "scope_ceiling", None)

        scope_str = f" [Scope ceiling: level {scope}]" if scope is not None else ""
        text_str = f' on "{text}"' if text else ""
        lines.append(f"{idx}. **[{kind.upper()}]** at `{loc}`{text_str}{scope_str}:\n   - Problem: {detail}")

    lines.append(closing)
    return "\n".join(lines)

