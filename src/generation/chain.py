"""Resume generation chain powered by Google Gemini LLM via LlamaIndex."""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from llama_index.core.llms import LLM, ChatMessage, MessageRole

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeLanguageCode,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.data.skills_map import reorganize_resume_skills
from src.generation.prompts import (
    SYSTEM_PROMPT,
    build_resume_generation_prompt,
    serialize_resume_for_llm,
)
from src.verification.text_utils import select_relevant_coursework

logger = logging.getLogger(__name__)


def extract_json_payload(text: str) -> str:
    """Extract a clean JSON substring from an LLM response string.

    Handles raw JSON, markdown-wrapped JSON (```json ... ```), or text with
    leading/trailing commentary.

    Args:
        text: Raw response string from the language model.

    Returns:
        str: Isolated JSON string.

    Raises:
        ValueError: If no valid JSON object boundaries are found.
    """
    cleaned = text.strip()

    # Case 1: Markdown code block (```json ... ``` or ``` ... ```)
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Case 2: Direct JSON object (find outer braces)
    start_idx = cleaned.find("{")
    end_idx = cleaned.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return cleaned[start_idx : end_idx + 1].strip()

    raise ValueError(f"Could not extract JSON payload from LLM response: {cleaned[:100]}...")


def parse_tailored_resume(raw_text: str) -> TailoredResume:
    """Parse and validate LLM output into a TailoredResume instance.

    Args:
        raw_text: Raw text string from the LLM.

    Returns:
        TailoredResume: Validated Pydantic resume model.

    Raises:
        ValueError: If JSON is invalid or fails Pydantic schema validation.
    """
    json_str = extract_json_payload(raw_text)
    try:
        data = json.loads(json_str)
        if isinstance(data, dict):
            # 1. Normalize header (injected deterministically; placeholder if omitted by LLM)
            if "header" not in data and "contact" in data:
                data["header"] = data.pop("contact")
            elif "header" not in data:
                data["header"] = {
                    "full_name": "",
                    "email": "",
                    "phone": "",
                    "location": "",
                }

            # 2. Normalize objective
            if "objective_or_summary" not in data:
                for k in ["professional_objective", "objective", "summary"]:
                    if k in data:
                        data["objective_or_summary"] = data.pop(k)
                        break

            # 3. Normalize education period
            if "education" in data and isinstance(data["education"], list):
                for edu in data["education"]:
                    if isinstance(edu, dict) and "period" not in edu:
                        start = edu.get("start_date", "")
                        end = edu.get("end_date", "")
                        edu["period"] = f"{start} - {end}".strip(" -") or "Present"

            # 4. Normalize experience period
            if "experiences" in data and isinstance(data["experiences"], list):
                for exp in data["experiences"]:
                    if isinstance(exp, dict) and "period" not in exp:
                        start = exp.get("start_date", "")
                        end = exp.get("end_date", "")
                        exp["period"] = f"{start} - {end}".strip(" -") or "Present"

            # 5. Normalize skills
            if "skills" in data and isinstance(data["skills"], dict):
                skills_list = []
                for cat_key, skill_items in data["skills"].items():
                    cat_name = cat_key.replace("_", " ").title()
                    if isinstance(skill_items, list):
                        skills_list.append({"category_name": cat_name, "skills": [str(s) for s in skill_items]})
                data["skills"] = skills_list
            elif "skills_categories" in data and "skills" not in data:
                data["skills"] = data.pop("skills_categories")

            if "skills" in data and isinstance(data["skills"], list):
                lang = data.get("language", "en")
                data["skills"] = [
                    cat.model_dump() if hasattr(cat, "model_dump") else cat
                    for cat in reorganize_resume_skills(data["skills"], language=lang)
                ]

            # 6. Normalize certifications
            if "certifications" in data and isinstance(data["certifications"], list):
                cert_strings = []
                for cert in data["certifications"]:
                    if isinstance(cert, dict):
                        name = cert.get("name", "")
                        issuer = cert.get("issuer", "")
                        date = cert.get("issue_date", "")
                        detail = f"{name} ({issuer}, {date})" if issuer and date else (f"{name} ({issuer})" if issuer else name)
                        cert_strings.append(detail)
                    elif isinstance(cert, str):
                        cert_strings.append(cert)
                data["certifications"] = cert_strings

        return TailoredResume.model_validate(data)
    except Exception as e:
        logger.error(
            "Failed to parse TailoredResume from JSON: %s\nPayload preview:\n%s",
            e,
            json_str[:300],
        )
        raise ValueError(f"Invalid TailoredResume structure: {e}") from e


def get_gemini_llm(
    model_name: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
) -> LLM:
    """Factory to create a configured Gemini LLM instance from LlamaIndex.

    Args:
        model_name: Identifier of the Gemini model. Defaults to settings.
        api_key: Gemini API key. Defaults to settings.
        temperature: Sampling temperature. Defaults to settings.

    Returns:
        LLM: Configured Gemini LLM adapter.
    """
    settings = get_settings()
    resolved_model = model_name or settings.generation_model
    if not resolved_model.startswith("models/"):
        resolved_model = f"models/{resolved_model}"
    resolved_key = api_key or settings.google_api_key
    resolved_temp = temperature if temperature is not None else settings.generation_temperature

    from llama_index.llms.gemini import Gemini

    return Gemini(
        model=resolved_model,
        api_key=resolved_key if resolved_key else None,
        temperature=resolved_temp,
    )


def detect_language_from_text(text: str) -> ResumeLanguageCode:
    """Detect whether text is predominantly Portuguese, English, or French.

    Uses scoring based on domain keywords and characteristic stopwords.

    Args:
        text: Input string (e.g. job posting title + description).

    Returns:
        ResumeLanguageCode: 'pt', 'en', or 'fr'.
    """
    if not text:
        return "pt"

    lower = text.lower()
    tokens = set(re.findall(r"\b\w+\b", lower))

    fr_words = {
        "stage", "stagiaire", "alternance", "missions", "profil", "recherché",
        "compétences", "formation", "connaissances", "équipe", "vous", "nous",
        "dans", "avec", "pour", "développement", "ingénieur", "poste", "recherche",
        "études", "bac", "autonomie", "projet", "projets", "anglais", "français",
        "candidat", "atouts", "durée", "domaine", "niveau",
    }
    pt_words = {
        "estágio", "estagiário", "vaga", "requisitos", "responsabilidades",
        "conhecimento", "desenvolvimento", "diferencial", "para", "com", "você",
        "nosso", "nossa", "equipe", "formação", "atividades", "bolsa", "semestre",
        "engenharia", "ciência", "computação", "superior", "cursando", "atuação",
    }
    en_words = {
        "internship", "intern", "job", "responsibilities", "requirements",
        "qualifications", "skills", "experience", "looking", "team", "with",
        "about", "role", "development", "engineering", "computer", "science",
        "working", "hands", "opportunity", "degree", "preferred", "join",
        "building", "grow", "full-time",
    }

    score_fr = len(tokens & fr_words)
    score_pt = len(tokens & pt_words)
    score_en = len(tokens & en_words)

    # Disambiguation weighting
    if re.search(r"\b(stage|stagiaire|alternance)\b", lower):
        score_fr += 4
    if re.search(r"\b(estágio|estagiário|cursando)\b", lower):
        score_pt += 4
    if re.search(r"\b(internship|intern)\b", lower):
        score_en += 4

    if score_fr > score_pt and score_fr > score_en:
        return "fr"
    if score_en > score_pt and score_en >= score_fr:
        return "en"
    if score_pt > score_en and score_pt >= score_fr:
        return "pt"

    return "en" if score_en > 0 else "pt"


def build_fallback_tailored_resume(
    candidate: CandidateProfile,
    job: JobPosting,
    language: ResumeLanguageCode = "pt",
) -> TailoredResume:
    """Build a deterministic, un-hallucinated fallback TailoredResume from candidate profile.

    Used when LLM generation fails or returns malformed data, ensuring the user still receives
    a high-quality, truthful, compilable resume.

    Args:
        candidate: CandidateProfile source of truth.
        job: Target JobPosting.
        language: Document language code ('pt', 'en', or 'fr').

    Returns:
        TailoredResume: Complete, valid resume based strictly on candidate facts.
    """
    header = ResumeHeader(
        full_name=candidate.contact.full_name,
        email=candidate.contact.email,
        phone=candidate.contact.phone,
        location=candidate.contact.location,
        linkedin_url=candidate.contact.linkedin_url,
        github_url=candidate.contact.github_url,
        portfolio_url=candidate.contact.portfolio_url,
    )

    if candidate.education:
        if language == "fr":
            objective = (
                f"Étudiant en {candidate.education[0].degree} à la recherche d'un stage "
                f"chez {job.company} pour appliquer ses compétences techniques "
                f"et contribuer à des projets à fort impact."
            )
        elif language == "en":
            objective = (
                f"Student in {candidate.education[0].degree} seeking an internship at "
                f"{job.company} to leverage technical fundamentals and "
                f"contribute to high-impact projects."
            )
        else:
            objective = (
                f"Estudante de {candidate.education[0].degree} buscando oportunidade de "
                f"estágio na {job.company} para aplicar fundamentos técnicos e "
                f"contribuir com entregas de alto impacto."
            )
    elif candidate.summary:
        objective = candidate.summary.strip()
    else:
        if language == "fr":
            objective = f"Recherche de stage chez {job.company}."
        elif language == "en":
            objective = f"Seeking an internship at {job.company}."
        else:
            objective = f"Buscando oportunidade de estágio na {job.company}."

    present_str = "Présent" if language == "fr" else ("Present" if language == "en" else "Presente")

    education_entries = []
    for edu in candidate.education:
        period_str = f"{edu.start_date} - {edu.end_date}".strip(" -")
        if edu.current:
            period_str = f"{edu.start_date} - {present_str}"
        highlights = list(edu.highlights) if edu.highlights else []
        if edu.gpa_or_honors:
            prefix = "Mention" if language == "fr" else ("Honors" if language == "en" else "Destaque")
            highlights.append(f"{prefix}: {edu.gpa_or_honors}")
        if edu.relevant_coursework:
            prefix_course = "Matières" if language == "fr" else ("Courses" if language == "en" else "Disciplinas")
            selected_courses = select_relevant_coursework(edu.relevant_coursework, job, max_courses=3)
            highlights.append(f"{prefix_course}: {', '.join(selected_courses)}")
        education_entries.append(
            ResumeEducation(
                institution=edu.institution,
                degree=edu.degree,
                period=period_str or present_str,
                highlights=highlights[:1] if len(candidate.education) > 2 else highlights,
            )
        )

    # Extract job tokens for ranking fallback items
    job_tokens = set()
    if hasattr(job, "technologies") and job.technologies:
        job_tokens.update(t.lower() for t in job.technologies)
    if hasattr(job, "keywords") and job.keywords:
        job_tokens.update(k.lower() for k in job.keywords)
    if hasattr(job, "title") and job.title:
        job_tokens.update(str(job.title).lower().split())

    experience_entries = []
    for exp in candidate.experiences:
        period_str = f"{exp.start_date} - {exp.end_date}".strip(" -")
        if exp.current:
            period_str = f"{exp.start_date} - {present_str}"

        # Prioritize leadership and job-relevant bullets
        def _exp_bullet_score(b: str) -> float:
            b_low = b.lower()
            score = 0.0
            if any(term in b_low for term in ("lead", "lider", "leader", "gestão", "coorden", "premi", "award", "destaque")):
                score += 5.0
            score += sum(1.5 for tok in job_tokens if len(tok) > 2 and tok in b_low)
            return score

        sorted_exp_bullets = sorted(exp.bullets, key=_exp_bullet_score, reverse=True)
        experience_entries.append(
            ResumeExperience(
                title=exp.title,
                organization=exp.organization,
                period=period_str or present_str,
                location=exp.location,
                bullets=list(sorted_exp_bullets)[:2],
                technologies=list(exp.technologies),
            )
        )

    # Rank projects by technical and keyword overlap with the target job
    def _proj_score(proj: Any) -> float:
        score = 0.0
        proj_techs = {t.lower() for t in getattr(proj, "technologies", [])}
        score += len(proj_techs & job_tokens) * 2.5
        proj_text = " ".join(getattr(proj, "bullets", [])).lower()
        score += sum(1.0 for tok in job_tokens if len(tok) > 2 and tok in proj_text)
        return score

    sorted_projects = sorted(candidate.projects, key=_proj_score, reverse=True)
    project_entries = []
    for proj in sorted_projects[:3]:
        project_entries.append(
            ResumeProject(
                name=proj.name,
                url=proj.url,
                bullets=list(proj.bullets)[:2],
                technologies=list(proj.technologies),
            )
        )

    cat_labels = {
        "fr": {
            "prog": "Langages de programmation",
            "frameworks": "Frameworks et bibliothèques",
            "db": "Bases de données",
            "tools": "Outils et plateformes",
            "soft": "Compétences relationnelles",
        },
        "en": {
            "prog": "Programming Languages",
            "frameworks": "Frameworks and Libraries",
            "db": "Databases",
            "tools": "Tools and Platforms",
            "soft": "Interpersonal Skills",
        },
        "pt": {
            "prog": "Linguagens de Programação",
            "frameworks": "Frameworks e Bibliotecas",
            "db": "Bancos de Dados",
            "tools": "Ferramentas e Plataformas",
            "soft": "Competências Interpessoais",
        },
    }
    c_names = cat_labels.get(language, cat_labels["pt"])

    skill_categories = []
    if candidate.skills.programming_languages:
        skill_categories.append(
            ResumeSkillCategory(
                category_name=c_names["prog"],
                skills=list(candidate.skills.programming_languages),
            )
        )
    if candidate.skills.frameworks_and_libraries:
        skill_categories.append(
            ResumeSkillCategory(
                category_name=c_names["frameworks"],
                skills=list(candidate.skills.frameworks_and_libraries),
            )
        )
    if candidate.skills.databases:
        skill_categories.append(
            ResumeSkillCategory(
                category_name=c_names["db"],
                skills=list(candidate.skills.databases),
            )
        )
    if candidate.skills.tools_and_platforms:
        skill_categories.append(
            ResumeSkillCategory(
                category_name=c_names["tools"],
                skills=list(candidate.skills.tools_and_platforms),
            )
        )
    if candidate.skills.soft_skills:
        skill_categories.append(
            ResumeSkillCategory(
                category_name=c_names["soft"],
                skills=list(candidate.skills.soft_skills),
            )
        )

    skill_categories = reorganize_resume_skills(skill_categories, language=language)

    language_entries = [
        ResumeLanguage(language=lang.language, proficiency=lang.proficiency)
        for lang in candidate.languages
    ]

    cert_entries = []
    for cert in candidate.certifications:
        if cert.issuer and cert.issue_date:
            cert_entries.append(f"{cert.name} ({cert.issuer}, {cert.issue_date})")
        elif cert.issuer:
            cert_entries.append(f"{cert.name} ({cert.issuer})")
        else:
            cert_entries.append(cert.name)

    return TailoredResume(
        target_job_title=job.title,
        target_company=job.company,
        header=header,
        objective_or_summary=objective,
        education=education_entries,
        experiences=experience_entries,
        projects=project_entries,
        skills=skill_categories,
        languages=language_entries,
        certifications=cert_entries,
        language=language,
    )


class ResumeGenerationChain:
    """Coordinates prompt construction, LLM invocation, and structured resume parsing.

    Attributes:
        llm: Language model adapter (Gemini in production, MockLLM in tests).
    """

    def __init__(self, llm: LLM | None = None) -> None:
        """Initialize the chain with an optional LLM instance.

        Args:
            llm: LLM instance. If None, initialized with get_gemini_llm().
        """
        self.llm = llm if llm is not None else get_gemini_llm()

    @staticmethod
    def resolve_language(job: JobPosting, language: str = "auto") -> ResumeLanguageCode:
        """Resolve the target language code, auto-detecting it from the job if needed.

        Args:
            job: Target JobPosting.
            language: Language code ('pt', 'en', 'fr') or 'auto' for auto-detection.

        Returns:
            ResumeLanguageCode: Resolved language code.
        """
        if language in ("pt", "en", "fr"):
            return language  # type: ignore[return-value]
        return detect_language_from_text(f"{job.title} {job.raw_description}")

    @staticmethod
    def build_messages(
        candidate: CandidateProfile,
        job: JobPosting,
        retrieved_guidelines: str,
        language: ResumeLanguageCode,
    ) -> list[ChatMessage]:
        """Build the system + user messages of the one-step generation prompt.

        Contact data is stripped from the candidate payload by
        :func:`build_resume_generation_prompt` (SEC-01).

        Args:
            candidate: CandidateProfile holding factual background.
            job: Target JobPosting.
            retrieved_guidelines: Recruitment advice (RAG context or full KB).
            language: Resolved language code.

        Returns:
            list[ChatMessage]: Messages for the first generation turn.
        """
        user_prompt = build_resume_generation_prompt(
            candidate=candidate,
            job=job,
            retrieved_guidelines=retrieved_guidelines,
            language=language,
        )
        return [
            ChatMessage(role=MessageRole.SYSTEM, content=SYSTEM_PROMPT),
            ChatMessage(role=MessageRole.USER, content=user_prompt),
        ]

    def invoke(self, messages: list[ChatMessage]) -> str:
        """Send messages to the LLM, retrying on rate-limit errors.

        Args:
            messages: Chat messages to send.

        Returns:
            str: Raw response text (may be empty).

        Raises:
            Exception: Any non rate-limit error, or the last rate-limit error.
        """
        max_retries = 3
        backoff_seconds = 7.0
        response_text = ""
        for attempt in range(1, max_retries + 1):
            try:
                response = self.llm.chat(messages)
                response_text = response.message.content or ""
                break
            except Exception as exc:
                err_msg = str(exc).lower()
                if ("429" in err_msg or "resource_exhausted" in err_msg or "quota" in err_msg) and attempt < max_retries:
                    logger.warning(
                        "Rate limit exceeded (attempt %d/%d). Sleeping %.1fs before retrying...",
                        attempt,
                        max_retries,
                        backoff_seconds,
                    )
                    time.sleep(backoff_seconds)
                    backoff_seconds *= 1.5
                else:
                    raise
        return response_text

    @staticmethod
    def finalize(
        response_text: str,
        candidate: CandidateProfile,
        language: ResumeLanguageCode,
    ) -> TailoredResume:
        """Parse an LLM response and inject the verified contact header.

        Args:
            response_text: Raw LLM response.
            candidate: CandidateProfile (source of the contact header).
            language: Resolved language code.

        Returns:
            TailoredResume: Parsed resume with deterministic header.

        Raises:
            ValueError: If the response cannot be parsed into a TailoredResume.
        """
        logger.info("LLM response received (%d chars). Parsing structure...", len(response_text))
        parsed_resume = parse_tailored_resume(response_text)
        parsed_resume.language = language
        # SEC-01: Deterministic injection of verified candidate contact data
        parsed_resume.header = ResumeHeader(
            full_name=candidate.contact.full_name,
            email=candidate.contact.email,
            phone=candidate.contact.phone,
            location=candidate.contact.location,
            linkedin_url=candidate.contact.linkedin_url,
            github_url=candidate.contact.github_url,
            portfolio_url=candidate.contact.portfolio_url,
        )
        return parsed_resume

    def generate(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
        retrieved_guidelines: str = "",
        allow_fallback: bool = False,
        language: str = "auto",
    ) -> TailoredResume:
        """Generate a tailored resume customized for a specific internship role.

        Args:
            candidate: CandidateProfile holding factual background.
            job: Target JobPosting.
            retrieved_guidelines: Optional recruitment advice from RAG retrieval.
            allow_fallback: If True, returns a deterministic un-hallucinated fallback
                resume upon LLM or parsing errors rather than raising an exception.
            language: Language code ('pt', 'en', 'fr') or 'auto' for auto-detection.

        Returns:
            TailoredResume: Structured, validated resume ready for LaTeX formatting.
        """
        resolved_lang = self.resolve_language(job, language)
        messages = self.build_messages(candidate, job, retrieved_guidelines, resolved_lang)

        logger.info(
            "Invoking LLM for job '%s' at '%s' (language=%s)...",
            job.title,
            job.company,
            resolved_lang,
        )

        try:
            response_text = self.invoke(messages)
            return self.finalize(response_text, candidate, resolved_lang)
        except Exception as exc:
            if allow_fallback:
                logger.warning(
                    "Resume generation failed (%s). Returning deterministic fallback resume.",
                    exc,
                )
                return build_fallback_tailored_resume(
                    candidate=candidate,
                    job=job,
                    language=resolved_lang,
                )
            raise

    def regenerate_with_feedback(
        self,
        candidate: CandidateProfile,
        base_messages: list[ChatMessage],
        history: list[tuple[TailoredResume, str]],
        language: ResumeLanguageCode,
    ) -> TailoredResume:
        """Regenerate a resume in a multi-turn conversation with verifier feedback (V1).

        Each previous resume is replayed as an assistant turn **without its header**
        (contact data never goes to the LLM), followed by the feedback message that
        lists its verification problems. No fallback is applied here: the caller (the
        V1 loop) decides what to do on failure.

        Args:
            candidate: CandidateProfile (source of the contact header).
            base_messages: Messages of the first generation turn.
            history: (previous resume, feedback prompt) pairs, oldest first.
            language: Resolved language code.

        Returns:
            TailoredResume: Regenerated resume with deterministic header.

        Raises:
            Exception: LLM or parsing errors are propagated.
        """
        messages = list(base_messages)
        for previous, feedback in history:
            messages.append(
                ChatMessage(role=MessageRole.ASSISTANT, content=serialize_resume_for_llm(previous))
            )
            messages.append(ChatMessage(role=MessageRole.USER, content=feedback))
        logger.info("Invoking LLM for regeneration round %d (language=%s)...", len(history), language)
        response_text = self.invoke(messages)
        return self.finalize(response_text, candidate, language)
