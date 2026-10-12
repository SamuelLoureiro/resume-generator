"""Run the deterministic verifiers on the real profile/facts and the Amazon golden fixtures.

These tests assert what the verifiers must find on the archived *bad* resume, what must
hold on the hand-corrected *good* resume, and that a resume built verbatim from the
profile is consistent with the verified facts. They do not claim the good fixture is
free of every defect: see ADR-018 in docs/decisions_log.md for the findings that remain.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts, load_candidate_facts
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeHeader,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
    TailoredResume,
)
from src.verification import VerificationReport, parse_tex_resume, verify_resume

ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = ROOT / "tests" / "golden" / "fixtures"
TRACK = "ai"


@pytest.fixture(scope="module")
def profile() -> CandidateProfile:
    return CandidateProfile.from_yaml(ROOT / "data" / "candidate_profile.yaml")


@pytest.fixture(scope="module")
def facts() -> CandidateFacts:
    return load_candidate_facts(ROOT / "data" / "candidate_facts.yaml")


def _report(name: str, profile: CandidateProfile, facts: CandidateFacts) -> VerificationReport:
    tex = (FIXTURES_DIR / f"{name}_amazon_resume.tex").read_text(encoding="utf-8")
    return verify_resume(parse_tex_resume(tex), profile, facts, track=TRACK, tex=tex)


@pytest.fixture(scope="module")
def bad(profile: CandidateProfile, facts: CandidateFacts) -> VerificationReport:
    return _report("bad", profile, facts)


@pytest.fixture(scope="module")
def good(profile: CandidateProfile, facts: CandidateFacts) -> VerificationReport:
    return _report("good", profile, facts)


# ---------------------------------------------------------------------------
# bad resume: the audited defects must be caught
# ---------------------------------------------------------------------------

def test_bad_resume_does_not_hard_pass(bad: VerificationReport) -> None:
    assert not bad.hard_pass


def test_bad_resume_inflated_verbs_are_caught(bad: VerificationReport) -> None:
    verbs = {i.verb for i in bad.inflation.inflated}
    assert {"architected", "designed"} <= verbs  # the two inflations of docs/audit_report.md


def test_bad_resume_pcb_inflation_cites_the_participation_ceiling(bad: VerificationReport) -> None:
    pcb = next(i for i in bad.inflation.inflated if i.verb == "designed")
    assert (pcb.fact_id, pcb.scope_ceiling) == ("exp_enib_pcb_design", 1)


def test_bad_resume_invented_project_url_is_caught(bad: VerificationReport) -> None:
    urls = [c for c in bad.fabrication.unsupported if c.kind == "url"]
    assert [c.text for c in urls] == ["https://github.com/SamuelLoureiro"]


def test_bad_resume_format_defects_are_caught(bad: VerificationReport) -> None:
    failed = {c.name for c in bad.format.failed}
    assert {"section_titles", "phone_format", "urls"} <= failed


def test_bad_resume_leadership_omission_is_a_critical_omission(bad: VerificationReport) -> None:
    assert bad.coverage is not None
    assert "exp_asimov_leadership" in bad.coverage.omissions


def test_bad_resume_unmatched_bullets_are_handed_to_the_judge(bad: VerificationReport) -> None:
    texts = " ".join(m.bullet for m in bad.inflation.unmatched)
    assert "distributed robotics network" in texts


def test_known_limitation_prose_claims_are_not_decided_deterministically(bad: VerificationReport) -> None:
    """'distributed systems' / 'scalable software' sit in free text: M1a-c cannot judge them."""
    flagged = " ".join(c.text for c in bad.fabrication.unsupported).lower()
    assert "distributed systems" not in flagged
    assert "scalable" not in flagged


# ---------------------------------------------------------------------------
# good resume: the corrected defects must stay corrected
# ---------------------------------------------------------------------------

def test_good_resume_achieves_hard_pass(good: VerificationReport) -> None:
    assert good.hard_pass is True
    assert good.fabrication.unsupported == []
    assert good.inflation.inflated == []
    assert good.format.failed == []


def test_good_resume_has_no_unsupported_skills_or_numbers(good: VerificationReport) -> None:
    assert good.fabrication.unsupported_of("a") == []
    assert good.fabrication.unsupported_of("b") == []


def test_good_resume_has_no_audited_verb_inflation(good: VerificationReport) -> None:
    assert not {"architected", "designed"} & {i.verb for i in good.inflation.inflated}


def test_good_resume_passes_the_audited_format_checks(good: VerificationReport) -> None:
    passed = {c.name for c in good.format.checks if c.status == "pass"}
    assert {"phone_format", "urls", "section_titles", "no_empty_entries", "single_language"} <= passed


def test_good_resume_keeps_the_leadership_fact(good: VerificationReport) -> None:
    assert good.coverage is not None
    assert "exp_asimov_leadership" in good.coverage.covered


def test_bad_resume_is_strictly_worse_than_good(bad: VerificationReport, good: VerificationReport) -> None:
    assert len(bad.inflation.inflated) > len(good.inflation.inflated)
    assert len(bad.format.failed) > len(good.format.failed)
    assert len(bad.fabrication.unsupported) > len(good.fabrication.unsupported)


# ---------------------------------------------------------------------------
# profile ↔ facts consistency
# ---------------------------------------------------------------------------

def _resume_from_profile(profile: CandidateProfile) -> TailoredResume:
    """Copy the profile into a resume without rewording anything."""
    s = profile.skills
    return TailoredResume(
        target_job_title="Software Intern",
        target_company="Example",
        header=ResumeHeader(**profile.contact.model_dump()),
        education=[
            ResumeEducation(
                institution=e.institution, degree=e.degree, period=f"{e.start_date} - {e.end_date}",
            )
            for e in profile.education
        ],
        experiences=[
            ResumeExperience(
                title=e.title, organization=e.organization, period=f"{e.start_date} - {e.end_date}",
                bullets=e.bullets, technologies=e.technologies,
            )
            for e in profile.experiences
        ],
        projects=[
            ResumeProject(name=p.name, url=p.url or None, bullets=p.bullets, technologies=p.technologies)
            for p in profile.projects
        ],
        skills=[
            ResumeSkillCategory(
                category_name="Skills",
                skills=[*s.programming_languages, *s.frameworks_and_libraries, *s.databases,
                        *s.tools_and_platforms, *s.soft_skills],
            )
        ],
        languages=[ResumeLanguage(language=l.language, proficiency=l.proficiency) for l in profile.languages],
        language="en",
    )


def test_profile_copied_verbatim_has_no_fabrication_and_no_inflation(
    profile: CandidateProfile, facts: CandidateFacts
) -> None:
    report = verify_resume(_resume_from_profile(profile), profile, facts, track=TRACK)
    assert report.fabrication.unsupported == [], [c.reason for c in report.fabrication.unsupported]
    assert report.inflation.inflated == [], [i.reason for i in report.inflation.inflated]
    assert report.inflation.assessed >= 10


def test_every_project_bullet_in_the_profile_maps_to_a_fact(
    profile: CandidateProfile, facts: CandidateFacts
) -> None:
    from src.verification.matching import match_resume_bullets

    matches = [m for m in match_resume_bullets(_resume_from_profile(profile), facts) if m.kind == "project"]
    unmatched = [m.bullet for m in matches if m.fact_id is None]
    assert unmatched == []
