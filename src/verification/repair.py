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
from src.generation.chain import build_fallback_tailored_resume
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
    summary_flagged = False

    for issue in issues:
        if not issue.is_truth_issue:
            continue
        if issue.location == "summary" or (issue.text and issue.text == resume.objective_or_summary):
            summary_flagged = True
        elif issue.location.startswith(("exp_", "proj_")):
            flagged_bullet_ids.add(issue.location)
        if issue.text and len(issue.text.split()) > 3:  # sentence-length text
            flagged_bullet_texts.add(issue.text.strip())

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
            )
            if not is_flagged:
                clean_bullets.append(bullet)
            else:
                actions.append(
                    RepairAction(
                        category="experience",
                        target=f"{exp.organization}/{b_id}",
                        action="drop_defective_bullet",
                        detail=f"Removed defective bullet: '{bullet[:60]}...'",
                    )
                )

        # Ensure experience is not empty
        if not clean_bullets and matched_p_exp.bullets:
            clean_bullets = list(matched_p_exp.bullets[:2])
            actions.append(
                RepairAction(
                    category="experience",
                    target=exp.organization,
                    action="restore_profile_bullets",
                    detail="Restored verified bullets from profile after removing defective claims.",
                )
            )

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
            )
            if not is_flagged:
                clean_bullets.append(bullet)
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
            clean_bullets = list(matched_p_proj.bullets[:2])
            actions.append(
                RepairAction(
                    category="project",
                    target=proj.name,
                    action="restore_profile_bullets",
                    detail="Restored verified project bullets from profile.",
                )
            )

        repaired_projects.append(
            ResumeProject(
                name=clean_name,
                url=clean_url,
                bullets=clean_bullets,
                technologies=clean_tech or list(matched_p_proj.technologies),
            )
        )

    # 4. Repair Education
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
        known_courses = set(matched_p_edu.relevant_coursework)
        for h in edu.highlights:
            # Check numbers
            if any(not truth.is_supported_number(n, extra_allowed_numbers) for n in extract_numbers(h)):
                continue
            clean_highlights.append(h)

        repaired_education.append(
            ResumeEducation(
                institution=clean_inst,
                degree=clean_degree,
                period=clean_period or present_str,
                location=matched_p_edu.institution,
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
                    f"Étudiant en {degree_str} à la recherche d'un stage "
                    f"chez {resume.target_company} pour appliquer ses compétences techniques "
                    f"et contribuer à des projets à fort impact."
                )
            else:
                repaired_summary = (
                    f"Student in {degree_str} seeking an internship at "
                    f"{resume.target_company} to leverage technical fundamentals and "
                    f"contribute to high-impact projects."
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
