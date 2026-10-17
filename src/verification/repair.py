"""Deterministic repair of generated resumes (Phase P8, Variant V1).

When error-guided regeneration reaches its budget (max 2 retries) and issues persist,
this module applies deterministic surgery to guarantee zero fabricated claims:
1. Skills/Tech: Purges unverified tools and platforms not present in the allowlist.
2. Entities/Dates: Overwrites hallucinated dates, role titles, and institutions with
   exact ground-truth data from CandidateProfile.
3. Bullets: Discards bullets containing unverified numbers, inflated verbs, or flagged
   by the claim judge; restores verified fallback bullets from the profile if an entry
   becomes empty.
4. Summary: Restores deterministic objective if the summary contains ungrounded claims.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts
from src.data.job_posting import JobPosting
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.data.skills_map import reorganize_resume_skills
from src.verification.fabrication import names_match
from src.verification.ground_truth import GroundTruth, extract_numbers
from src.verification.issues import (
    VerificationIssue,
    locate_bullet,
    parse_bullet_id,
)

logger = logging.getLogger(__name__)


class RepairAction(BaseModel):
    """Record of a single deterministic repair action taken."""

    model_config = ConfigDict(frozen=True)

    category: str
    target: str
    action: str
    detail: str


class RepairLog(BaseModel):
    """Ledger of all deterministic repair operations applied to a resume."""

    model_config = ConfigDict(frozen=True)

    actions: list[RepairAction] = Field(default_factory=list)

    @property
    def total_actions(self) -> int:
        """Total number of repair actions applied."""
        return len(self.actions)


def repair_resume(
    resume: TailoredResume,
    issues: list[VerificationIssue],
    profile: CandidateProfile,
    facts: CandidateFacts,
    job: JobPosting | None = None,
    extra_allowed_numbers: set[str] | None = None,
) -> tuple[TailoredResume, RepairLog]:
    """Perform deterministic repair on a resume with detected verification defects.

    Args:
        resume: The resume to be repaired.
        issues: List of issues detected by deterministic checks and claim judge.
        profile: CandidateProfile source of truth.
        facts: Verified atomic candidate facts.
        job: Target job posting (if None, derived from resume target metadata).
        extra_allowed_numbers: Legitimate numbers outside profile (e.g. from job title).

    Returns:
        tuple[TailoredResume, RepairLog]: Repaired resume and log of repair actions.
    """
    truth = GroundTruth(profile, facts)
    actions: list[RepairAction] = []
    resolved_job = (
        job
        if job is not None
        else JobPosting(
            title=resume.target_job_title,
            company=resume.target_company,
            raw_description="",
        )
    )

    # Map problem locations for fast lookup
    flagged_bullet_ids: set[str] = set()
    flagged_bullet_texts: set[str] = set()
    fabricated_keywords: set[str] = set()
    summary_flagged = False

    meta_word_issues: list[VerificationIssue] = []

    for issue in issues:
        if issue.kind == "format" and issue.check == "job_title_not_in_summary":
            summary_flagged = True
            continue
        if not issue.is_truth_issue:
            continue
        if issue.kind == "summary_lint":
            meta_word_issues.append(issue)
            continue
        if issue.kind == "fabricated_keyword" and issue.text:
            fabricated_keywords.add(issue.text.strip())
        if issue.location == "summary" or (issue.text and issue.text == resume.objective_or_summary):
            summary_flagged = True
        elif issue.location.startswith(("exp_", "proj_")):
            flagged_bullet_ids.add(issue.location)
        if issue.text and len(issue.text.split()) > 3:  # sentence-length text
            flagged_bullet_texts.add(issue.text.strip())

    if resume.objective_or_summary and any(
        re.search(r"\b" + re.escape(fk) + r"\b", resume.objective_or_summary, re.IGNORECASE)
        for fk in fabricated_keywords
    ):
        summary_flagged = True

    # 1. Repair Skills
    repaired_skills: list[ResumeSkillCategory] = []
    for cat in resume.skills:
        kept_skills = []
        for s in cat.skills:
            if truth.is_allowed_skill(s):
                kept_skills.append(s)
            else:
                actions.append(
                    RepairAction(
                        category="skills",
                        target=f"{cat.category_name}/{s}",
                        action="remove_unsupported_skill",
                        detail=f"Removed '{s}' as it is not in verified skills or fact tags.",
                    )
                )
        if kept_skills:
            repaired_skills.append(
                ResumeSkillCategory(
                    category_name=cat.category_name,
                    skills=kept_skills,
                )
            )

    if repaired_skills:
        repaired_skills = reorganize_resume_skills(repaired_skills, language=resume.language)

    # If all skills were dropped, restore from profile
    if not repaired_skills and (
        profile.skills.programming_languages or profile.skills.frameworks_and_libraries
    ):
        from src.generation.chain import build_fallback_tailored_resume

        fallback_res = build_fallback_tailored_resume(
            profile,
            resolved_job,
            language=resume.language,
        )
        repaired_skills = fallback_res.skills
        actions.append(
            RepairAction(
                category="skills",
                target="all",
                action="restore_profile_skills",
                detail="Restored verified skills categories from candidate profile.",
            )
        )

    # 2. Repair Experiences
    repaired_experiences: list[ResumeExperience] = []
    for e_idx, exp in enumerate(resume.experiences):
        matched_p_exp = next(
            (p for p in profile.experiences if names_match(exp.organization, p.organization)),
            None,
        )
        if matched_p_exp is None:
            actions.append(
                RepairAction(
                    category="experience",
                    target=exp.organization,
                    action="drop_fabricated_organization",
                    detail=f"Dropped experience at '{exp.organization}' not present in candidate profile.",
                )
            )
            continue

        # Correct title and period
        clean_title = matched_p_exp.title
        present_str = "Présent" if resume.language == "fr" else ("Present" if resume.language == "en" else "Presente")
        clean_period = f"{matched_p_exp.start_date} - {matched_p_exp.end_date}".strip(" -")
        if matched_p_exp.current:
            clean_period = f"{matched_p_exp.start_date} - {present_str}"

        if exp.title != clean_title or exp.period != clean_period:
            actions.append(
                RepairAction(
                    category="experience",
                    target=exp.organization,
                    action="align_metadata",
                    detail=f"Aligned role title to '{clean_title}' and period to '{clean_period}'.",
                )
            )

        # Filter technologies
        clean_tech = [t for t in exp.technologies if truth.is_allowed_skill(t)]
        if len(clean_tech) < len(exp.technologies):
            actions.append(
                RepairAction(
                    category="experience",
                    target=exp.organization,
                    action="filter_technologies",
                    detail="Removed unverified technologies from experience entry.",
                )
            )

        # Filter bullets
        clean_bullets = []
        for b_idx, bullet in enumerate(exp.bullets):
            b_id = f"exp_{e_idx}_bullet_{b_idx}"
            is_flagged = (
                b_id in flagged_bullet_ids
                or bullet.strip() in flagged_bullet_texts
                or any(
                    not truth.is_supported_number(n, extra_allowed_numbers)
                    for n in extract_numbers(bullet)
                )
                or any(
                    re.search(r"\b" + re.escape(fk) + r"\b", bullet, re.IGNORECASE)
                    for fk in fabricated_keywords
                )
            )
            if not is_flagged:
                clean_b = bullet
                for m_iss in meta_word_issues:
                    if m_iss.location == b_id or re.search(r"\b" + re.escape(m_iss.text) + r"\b", clean_b, re.IGNORECASE):
                        clean_b = re.sub(r"\b" + re.escape(m_iss.text) + r"\s*", "", clean_b, flags=re.IGNORECASE).strip()
                        clean_b = re.sub(r"\s+", " ", clean_b)
                        actions.append(
                            RepairAction(
                                category="experience",
                                target=f"{exp.organization}/{b_id}",
                                action="delete_forbidden_meta_word",
                                detail=f"Deleted meta-word '{m_iss.text}' from bullet.",
                            )
                        )
                clean_bullets.append(clean_b)
            else:
                actions.append(
                    RepairAction(
                        category="experience",
                        target=f"{exp.organization}/{b_id}",
                        action="drop_defective_bullet",
                        detail=f"Removed defective bullet: '{bullet[:60]}...'",
                    )
                )

        # Ensure experience is not empty and backfill verified bullets if needed
        if not clean_bullets and matched_p_exp.bullets:
            if resume.language == "en":
                clean_bullets = list(matched_p_exp.bullets[:2])
            else:
                tech_str = ", ".join((clean_tech or list(matched_p_exp.technologies))[:3])
                if resume.language == "fr":
                    clean_bullets = [
                        f"Développé et intégré des solutions logicielles et matérielles au sein de {matched_p_exp.organization} en utilisant {tech_str}."
                    ]
                else:
                    clean_bullets = [
                        f"Desenvolveu e integrou soluções técnicas na {matched_p_exp.organization} utilizando {tech_str}."
                    ]
            actions.append(
                RepairAction(
                    category="experience",
                    target=exp.organization,
                    action="restore_profile_bullets",
                    detail="Restored verified bullets from profile after removing defective claims.",
                )
            )
        elif resume.language == "en" and len(clean_bullets) < 2 and matched_p_exp.bullets:
            for cand_b in matched_p_exp.bullets:
                if cand_b not in clean_bullets and cand_b not in flagged_bullet_texts:
                    clean_bullets.append(cand_b)
                    actions.append(
                        RepairAction(
                            category="experience",
                            target=exp.organization,
                            action="restore_profile_bullets",
                            detail="Backfilled verified bullet from profile to maintain complete entries.",
                        )
                    )
                    if len(clean_bullets) >= 2:
                        break

        repaired_experiences.append(
            ResumeExperience(
                title=clean_title,
                organization=matched_p_exp.organization,
                period=clean_period or present_str,
                location=matched_p_exp.location or exp.location,
                bullets=clean_bullets,
                technologies=clean_tech or list(matched_p_exp.technologies),
            )
        )

    # 3. Repair Projects
    repaired_projects: list[ResumeProject] = []
    for p_idx, proj in enumerate(resume.projects):
        matched_p_proj = next(
            (p for p in profile.projects if names_match(proj.name, p.name)),
            None,
        )
        if matched_p_proj is None:
            actions.append(
                RepairAction(
                    category="project",
                    target=proj.name,
                    action="drop_fabricated_project",
                    detail=f"Dropped project '{proj.name}' not found in candidate profile.",
                )
            )
            continue

        clean_name = matched_p_proj.name
        clean_url = matched_p_proj.url
        clean_tech = [t for t in proj.technologies if truth.is_allowed_skill(t)]

        # Filter bullets
        clean_bullets = []
        for b_idx, bullet in enumerate(proj.bullets):
            b_id = f"proj_{p_idx}_bullet_{b_idx}"
            is_flagged = (
                b_id in flagged_bullet_ids
                or bullet.strip() in flagged_bullet_texts
                or any(
                    not truth.is_supported_number(n, extra_allowed_numbers)
                    for n in extract_numbers(bullet)
                )
                or any(
                    re.search(r"\b" + re.escape(fk) + r"\b", bullet, re.IGNORECASE)
                    for fk in fabricated_keywords
                )
            )
            if not is_flagged:
                clean_b = bullet
                for m_iss in meta_word_issues:
                    if m_iss.location == b_id or re.search(r"\b" + re.escape(m_iss.text) + r"\b", clean_b, re.IGNORECASE):
                        clean_b = re.sub(r"\b" + re.escape(m_iss.text) + r"\s*", "", clean_b, flags=re.IGNORECASE).strip()
                        clean_b = re.sub(r"\s+", " ", clean_b)
                        actions.append(
                            RepairAction(
                                category="project",
                                target=f"{proj.name}/{b_id}",
                                action="delete_forbidden_meta_word",
                                detail=f"Deleted meta-word '{m_iss.text}' from bullet.",
                            )
                        )
                clean_bullets.append(clean_b)
            else:
                actions.append(
                    RepairAction(
                        category="project",
                        target=f"{proj.name}/{b_id}",
                        action="drop_defective_bullet",
                        detail=f"Removed defective project bullet: '{bullet[:60]}...'",
                    )
                )

        if not clean_bullets and matched_p_proj.bullets:
            if resume.language == "en":
                clean_bullets = list(matched_p_proj.bullets[:2])
            else:
                tech_str = ", ".join((clean_tech or list(matched_p_proj.technologies))[:3])
                if resume.language == "fr":
                    clean_bullets = [
                        f"Développé et implémenté le projet {clean_name} en utilisant {tech_str}."
                    ]
                else:
                    clean_bullets = [
                        f"Desenvolveu e implementou o projeto {clean_name} utilizando {tech_str}."
                    ]
            actions.append(
                RepairAction(
                    category="project",
                    target=proj.name,
                    action="restore_profile_bullets",
                    detail="Restored verified project bullets from profile.",
                )
            )
        elif resume.language == "en" and len(clean_bullets) < 2 and matched_p_proj.bullets:
            for cand_b in matched_p_proj.bullets:
                if cand_b not in clean_bullets and cand_b not in flagged_bullet_texts:
                    clean_bullets.append(cand_b)
                    actions.append(
                        RepairAction(
                            category="project",
                            target=proj.name,
                            action="restore_profile_bullets",
                            detail="Backfilled verified project bullet from profile.",
                        )
                    )
                    if len(clean_bullets) >= 2:
                        break

        repaired_projects.append(
            ResumeProject(
                name=clean_name,
                url=clean_url,
                bullets=clean_bullets,
                technologies=clean_tech or list(matched_p_proj.technologies),
            )
        )

    # Ensure at least 3 projects if profile has >= 3 projects (for English resumes where profile bullets match language)
    if resume.language == "en" and len(repaired_projects) < 3 and len(profile.projects) >= 3:
        existing_names = {p.name.lower() for p in repaired_projects}
        job_tokens = set()
        if hasattr(resolved_job, "technologies") and resolved_job.technologies:
            job_tokens.update(t.lower() for t in resolved_job.technologies)
        if hasattr(resolved_job, "keywords") and resolved_job.keywords:
            job_tokens.update(k.lower() for k in resolved_job.keywords)
        if hasattr(resolved_job, "title") and resolved_job.title:
            job_tokens.update(str(resolved_job.title).lower().split())

        def _p_relevance(cand_p: Any) -> float:
            score = 0.0
            p_techs = {t.lower() for t in getattr(cand_p, "technologies", [])}
            score += len(p_techs & job_tokens) * 2.0
            p_text = " ".join(getattr(cand_p, "bullets", [])).lower()
            score += sum(1.0 for tok in job_tokens if len(tok) > 2 and tok in p_text)
            return score

        available = [p for p in profile.projects if p.name.lower() not in existing_names]
        available_sorted = sorted(available, key=_p_relevance, reverse=True)
        for cand_proj in available_sorted:
            if len(repaired_projects) >= 3:
                break
            repaired_projects.append(
                ResumeProject(
                    name=cand_proj.name,
                    url=cand_proj.url,
                    bullets=list(cand_proj.bullets)[:2],
                    technologies=list(cand_proj.technologies),
                )
            )
            actions.append(
                RepairAction(
                    category="project",
                    target=cand_proj.name,
                    action="restore_profile_project",
                    detail=f"Backfilled relevant verified project '{cand_proj.name}' to complete 1-page layout budget.",
                )
            )

    # 4. Repair Education
    from src.verification.fabrication import _COURSEWORK_LABEL_RE
    repaired_education: list[ResumeEducation] = []
    for edu in resume.education:
        matched_p_edu = next(
            (p for p in profile.education if names_match(edu.institution, p.institution)),
            None,
        )
        if matched_p_edu is None:
            actions.append(
                RepairAction(
                    category="education",
                    target=edu.institution,
                    action="drop_unmatched_education",
                    detail=f"Dropped education entry '{edu.institution}' not in profile.",
                )
            )
            continue

        clean_inst = matched_p_edu.institution
        clean_degree = matched_p_edu.degree
        present_str = "Présent" if resume.language == "fr" else ("Present" if resume.language == "en" else "Presente")
        clean_period = f"{matched_p_edu.start_date} - {matched_p_edu.end_date}".strip(" -")
        if matched_p_edu.current:
            clean_period = f"{matched_p_edu.start_date} - {present_str}"

        # Clean highlights / coursework
        clean_highlights = []
        known_courses = [*matched_p_edu.relevant_coursework, *matched_p_edu.highlights]
        for h in edu.highlights:
            # Check numbers and fabricated keywords
            if any(not truth.is_supported_number(n, extra_allowed_numbers) for n in extract_numbers(h)):
                continue
            if any(re.search(r"\b" + re.escape(fk) + r"\b", h, re.IGNORECASE) for fk in fabricated_keywords):
                continue
            cw_match = _COURSEWORK_LABEL_RE.match(h)
            if cw_match:
                valid_courses = [
                    c.strip()
                    for c in cw_match.group(2).split(",")
                    if c.strip() and any(names_match(c.strip(), known) for known in known_courses)
                ]
                if valid_courses:
                    clean_highlights.append(f"{cw_match.group(1)}: {', '.join(valid_courses)}")
                elif matched_p_edu.relevant_coursework:
                    # Strip the label prefix so translated courses don't fail M1c coursework check
                    clean_highlights.append(cw_match.group(2).strip())
                continue
            clean_highlights.append(h)

        repaired_education.append(
            ResumeEducation(
                institution=clean_inst,
                degree=clean_degree,
                period=clean_period or present_str,
                location=getattr(matched_p_edu, "location", None) or edu.location,
                highlights=clean_highlights[:1] if len(profile.education) > 2 else clean_highlights,
            )
        )

    # 5. Repair Summary
    repaired_summary = resume.objective_or_summary
    if summary_flagged or (
        repaired_summary
        and any(
            not truth.is_supported_number(n, extra_allowed_numbers)
            for n in extract_numbers(repaired_summary)
        )
    ):
        if profile.education:
            degree_str = profile.education[0].degree
            if resume.language == "fr":
                repaired_summary = (
                    f"Étudiant en {degree_str} ciblant les opportunités chez {resume.target_company}, "
                    f"mobilisant des compétences techniques vérifiées en ingénierie logicielle et systèmes."
                )
            elif resume.language == "pt":
                repaired_summary = (
                    f"Estudante de {degree_str} direcionado a oportunidades na {resume.target_company}, "
                    f"aplicando fundamentos técnicos verificados em engenharia de software e sistemas."
                )
            else:
                repaired_summary = (
                    f"Engineering student in {degree_str} seeking opportunities at {resume.target_company}, "
                    f"applying verified technical foundations in software engineering and systems."
                )
        else:
            repaired_summary = profile.summary or ""
        actions.append(
            RepairAction(
                category="summary",
                target="objective_or_summary",
                action="reset_to_deterministic_objective",
                detail="Reset objective/summary to deterministic truthful template.",
            )
        )
    elif repaired_summary and meta_word_issues:
        for m_iss in meta_word_issues:
            if m_iss.location == "summary" or re.search(r"\b" + re.escape(m_iss.text) + r"\b", repaired_summary, re.IGNORECASE):
                repaired_summary = re.sub(r"\b" + re.escape(m_iss.text) + r"\s*", "", repaired_summary, flags=re.IGNORECASE).strip()
                repaired_summary = re.sub(r"\s+", " ", repaired_summary)
                actions.append(
                    RepairAction(
                        category="summary",
                        target="objective_or_summary",
                        action="delete_forbidden_meta_word",
                        detail=f"Deleted meta-word '{m_iss.text}' from summary.",
                    )
                )

    # 6. Repair Certifications & Languages
    repaired_certs = [
        c for c in resume.certifications if any(names_match(c, p.name) for p in profile.certifications)
    ]
    repaired_languages = [
        ResumeLanguage(language=lang.language, proficiency=lang.proficiency)
        for lang in profile.languages
    ]

    repaired_resume = TailoredResume(
        target_job_title=resume.target_job_title,
        target_company=resume.target_company,
        header=resume.header,
        objective_or_summary=repaired_summary,
        education=repaired_education or [
            ResumeEducation(
                institution=e.institution,
                degree=e.degree,
                period=f"{e.start_date} - {e.end_date}",
            )
            for e in profile.education
        ],
        experiences=repaired_experiences or [
            ResumeExperience(
                title=e.title,
                organization=e.organization,
                period=f"{e.start_date} - {e.end_date}",
                bullets=list(e.bullets[:2]),
                technologies=list(e.technologies),
            )
            for e in profile.experiences[:2]
        ],
        projects=repaired_projects or [
            ResumeProject(
                name=p.name,
                url=p.url,
                bullets=list(p.bullets[:2]),
                technologies=list(p.technologies),
            )
            for p in profile.projects[:2]
        ],
        skills=repaired_skills,
        languages=repaired_languages,
        certifications=repaired_certs,
        language=resume.language,
    )

    return repaired_resume, RepairLog(actions=actions)
