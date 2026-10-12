"""Unit tests for the deterministic metrics M1 (a–c), M2, M3 and M4 (offline, synthetic data)."""

from __future__ import annotations

import pytest

from src.data.facts import AtomicFact, CandidateFacts
from src.data.resume import (
    ResumeEducation,
    ResumeExperience,
    ResumeLanguage,
    ResumeProject,
    ResumeSkillCategory,
)
from src.verification import (
    GroundTruth,
    check_coverage,
    check_fabrication,
    check_inflation,
    check_keywords,
    verify_resume,
)
from tests.verification_data import make_facts, make_job, make_profile, make_resume


@pytest.fixture
def truth() -> GroundTruth:
    return GroundTruth(make_profile(), make_facts())


def _kinds(result) -> set[tuple[str, str]]:
    return {(c.sub, c.kind) for c in result.unsupported}


# ---------------------------------------------------------------------------
# M1a — skills
# ---------------------------------------------------------------------------

def test_m1_clean_resume_has_no_unsupported_claims(truth: GroundTruth) -> None:
    result = check_fabrication(make_resume(), truth)
    assert result.unsupported == []
    assert result.rate == 0.0
    assert result.total_claims > 10


def test_m1a_fake_skill_is_caught(truth: GroundTruth) -> None:
    resume = make_resume(
        skills=[ResumeSkillCategory(category_name="Tools", skills=["Docker", "Kubernetes"])]
    )
    result = check_fabrication(resume, truth)
    assert [(c.kind, c.text) for c in result.unsupported_of("a")] == [("skill", "Kubernetes")]


def test_m1a_fake_technology_in_experience_and_project_is_caught(truth: GroundTruth) -> None:
    resume = make_resume(
        experiences=[
            ResumeExperience(
                title="Backend Intern", organization="Acme Corp", period="06/2023 - 09/2023",
                bullets=["Participated in code reviews for the billing team."],
                technologies=["Python", "Spark"],
            )
        ],
        projects=[ResumeProject(name="Task API", bullets=["x"], technologies=["FastAPI", "Terraform"])],
    )
    texts = {c.text for c in check_fabrication(resume, truth).unsupported_of("a")}
    assert texts == {"Spark", "Terraform"}


def test_m1a_composite_with_one_unknown_part_counts_once(truth: GroundTruth) -> None:
    resume = make_resume(skills=[ResumeSkillCategory(category_name="X", skills=["Python (Pandas)"])])
    assert len(check_fabrication(resume, truth).unsupported_of("a")) == 1


# ---------------------------------------------------------------------------
# M1b — numbers
# ---------------------------------------------------------------------------

def _resume_with_bullet(bullet: str, summary: str | None = None):
    return make_resume(
        objective_or_summary=summary,
        experiences=[
            ResumeExperience(
                title="Backend Intern", organization="Acme Corp", period="06/2023 - 09/2023",
                bullets=[bullet], technologies=["Python"],
            )
        ],
    )


def test_m1b_fake_percentage_is_caught(truth: GroundTruth) -> None:
    result = check_fabrication(_resume_with_bullet("Built REST APIs and cut latency by 60%."), truth)
    assert [c.text for c in result.unsupported_of("b")] == ["60%"]


def test_m1b_verified_metric_passes(truth: GroundTruth) -> None:
    result = check_fabrication(_resume_with_bullet("Cut report time by 40% for the billing service."), truth)
    assert result.unsupported_of("b") == []


def test_m1b_inflated_suffix_is_caught(truth: GroundTruth) -> None:
    result = check_fabrication(_resume_with_bullet("Led a team of 4+ students."), truth)
    assert [c.text for c in result.unsupported_of("b")] == ["4+"]


def test_m1b_phone_digits_cannot_support_a_number(truth: GroundTruth) -> None:
    result = check_fabrication(_resume_with_bullet("Served 7 enterprise clients."), truth)
    assert [c.text for c in result.unsupported_of("b")] == ["7"]


def test_m1b_numbers_in_summary_are_checked(truth: GroundTruth) -> None:
    result = check_fabrication(make_resume(objective_or_summary="Delivered 12 projects."), truth)
    assert [c.text for c in result.unsupported_of("b")] == ["12"]


def test_m1b_year_not_in_profile_is_caught_unless_explicitly_allowed(truth: GroundTruth) -> None:
    resume = make_resume(objective_or_summary="Seeking the 2027 internship.")
    assert [c.text for c in check_fabrication(resume, truth).unsupported_of("b")] == ["2027"]
    allowed = check_fabrication(resume, truth, extra_allowed_numbers={"2027"})
    assert allowed.unsupported_of("b") == []


def test_m1b_year_present_in_profile_dates_is_supported(truth: GroundTruth) -> None:
    resume = make_resume(objective_or_summary="Backend intern since 2023.")
    assert check_fabrication(resume, truth).unsupported_of("b") == []


# ---------------------------------------------------------------------------
# M1c — entities, titles, dates
# ---------------------------------------------------------------------------

def _with_experience(**fields: object):
    base = dict(
        title="Backend Intern", organization="Acme Corp", period="06/2023 - 09/2023",
        bullets=["Participated in code reviews for the billing team."], technologies=["Python"],
    )
    base.update(fields)
    return make_resume(experiences=[ResumeExperience(**base)], projects=[])  # type: ignore[arg-type]


def test_m1c_fake_employer_is_caught(truth: GroundTruth) -> None:
    result = check_fabrication(_with_experience(organization="Gamma Inc"), truth)
    assert ("c", "organization") in _kinds(result)


def test_m1c_inflated_title_is_caught(truth: GroundTruth) -> None:
    result = check_fabrication(_with_experience(title="Senior Backend Engineer"), truth)
    assert ("c", "title") in _kinds(result)


def test_m1c_wrong_dates_are_caught(truth: GroundTruth) -> None:
    result = check_fabrication(_with_experience(period="06/2022 - 09/2023"), truth)
    assert ("c", "period") in _kinds(result)


def test_m1c_year_only_period_is_accepted_when_years_match(truth: GroundTruth) -> None:
    assert ("c", "period") not in _kinds(check_fabrication(_with_experience(period="2023 - 2023"), truth))


def test_m1c_unpadded_month_is_normalized(truth: GroundTruth) -> None:
    assert ("c", "period") not in _kinds(check_fabrication(_with_experience(period="6/2023 - 9/2023"), truth))


def test_m1c_present_requires_current_role(truth: GroundTruth) -> None:
    wrong = check_fabrication(_with_experience(period="06/2023 - Present"), truth)
    assert ("c", "period") in _kinds(wrong)
    ok = check_fabrication(
        _with_experience(title="Research Assistant", organization="Beta Labs", period="01/2024 - Présent",
                         bullets=["Led a team of 4 students running annotation experiments."],
                         technologies=["PyTorch"]),
        truth,
    )
    assert ("c", "period") not in _kinds(ok)


def test_m1c_organization_may_be_a_subset_of_the_profile_name(truth: GroundTruth) -> None:
    assert ("c", "organization") not in _kinds(check_fabrication(_with_experience(organization="Acme"), truth))


def test_m1c_education_mismatches(truth: GroundTruth) -> None:
    def edu(**f: object):
        base = dict(institution="University of Paris", degree="BSc Computer Science", period="09/2021 - 06/2024")
        base.update(f)
        return make_resume(education=[ResumeEducation(**base)])  # type: ignore[arg-type]

    assert ("c", "institution") in _kinds(check_fabrication(edu(institution="MIT"), truth))
    assert ("c", "degree") in _kinds(check_fabrication(edu(degree="PhD Computer Science"), truth))
    assert ("c", "period") in _kinds(check_fabrication(edu(period="09/2021 - 06/2026"), truth))
    assert check_fabrication(edu(), truth).unsupported == []


def test_m1c_invented_coursework_is_caught(truth: GroundTruth) -> None:
    resume = make_resume(
        education=[
            ResumeEducation(
                institution="University of Paris", degree="BSc Computer Science",
                period="09/2021 - 06/2024",
                highlights=["Relevant Coursework: Algorithms, Quantum Computing"],
            )
        ]
    )
    result = check_fabrication(resume, truth)
    assert [c.text for c in result.unsupported if c.kind == "coursework"] == ["Quantum Computing"]


def test_m1c_project_name_and_url(truth: GroundTruth) -> None:
    fake_name = make_resume(projects=[ResumeProject(name="Hyperloop", bullets=["x"])])
    assert ("c", "project") in _kinds(check_fabrication(fake_name, truth))

    wrong_url = make_resume(
        projects=[ResumeProject(name="Task API", url="https://github.com/jane", bullets=["x"])]
    )
    assert ("c", "url") in _kinds(check_fabrication(wrong_url, truth))

    invented_url = make_resume(
        projects=[ResumeProject(name="Notes", url="https://github.com/jane/notes", bullets=["x"])]
    )
    assert ("c", "url") in _kinds(check_fabrication(invented_url, truth))  # profile has no URL for Notes

    ok = make_resume(
        projects=[ResumeProject(name="Task API", url="github.com/jane/task-api/", bullets=["x"])]
    )
    assert ("c", "url") not in _kinds(check_fabrication(ok, truth))


def test_m1c_fake_certification_and_language(truth: GroundTruth) -> None:
    resume = make_resume(
        certifications=["AWS Cloud Practitioner", "Google Cloud Architect"],
        languages=[ResumeLanguage(language="German", proficiency="Fluent")],
    )
    result = check_fabrication(resume, truth)
    assert [c.text for c in result.unsupported if c.kind == "certification"] == ["Google Cloud Architect"]
    assert ("c", "language") in _kinds(result)


def test_m1c_language_proficiency_inflation_is_caught(truth: GroundTruth) -> None:
    resume = make_resume(languages=[ResumeLanguage(language="English", proficiency="Native")])
    assert ("c", "proficiency") in _kinds(check_fabrication(resume, truth))


def test_m1c_localized_language_names_and_levels(truth: GroundTruth) -> None:
    resume = make_resume(
        languages=[
            ResumeLanguage(language="Inglês", proficiency="Avançado (C1)"),
            ResumeLanguage(language="Português", proficiency="Nativo"),
        ]
    )
    assert check_fabrication(resume, truth).unsupported_of("c") == []


def test_m1c_candidate_name_must_match(truth: GroundTruth) -> None:
    header = make_resume().header.model_copy(update={"full_name": "John Smith"})
    assert ("c", "name") in _kinds(check_fabrication(make_resume(header=header), truth))


def test_m1_empty_resume_is_not_a_crash(truth: GroundTruth) -> None:
    resume = make_resume(
        objective_or_summary=None, education=[], experiences=[], projects=[], skills=[],
        languages=[], certifications=[],
    )
    result = check_fabrication(resume, truth)
    assert result.unsupported == []
    assert result.total_claims == 1  # only the candidate name
    nothing = check_fabrication(
        make_resume(header=make_resume().header.model_copy(update={"full_name": ""}),
                    objective_or_summary=None, education=[], experiences=[], projects=[], skills=[],
                    languages=[], certifications=[]),
        truth,
    )
    assert nothing.rate is not None  # the empty name is itself an unsupported claim
    assert len(nothing.unsupported) == 1


def test_m1_special_characters_do_not_break_checks(truth: GroundTruth) -> None:
    resume = make_resume(
        objective_or_summary="R&D focus — 100% backend; C# & C++ \\ ~ ^ {x}",
        skills=[ResumeSkillCategory(category_name="Misc", skills=["C++", "C#", "R&D"])],
    )
    result = check_fabrication(resume, truth)
    assert {c.text for c in result.unsupported_of("a")} == {"C#", "R&D"}


# ---------------------------------------------------------------------------
# M2 — inflation
# ---------------------------------------------------------------------------

def test_m2_clean_resume_has_no_inflation() -> None:
    result = check_inflation(make_resume(), make_facts())
    assert result.inflated == []
    assert result.assessed == 4
    assert result.rate == 0.0


def test_m2_lead_verb_above_ceiling_is_inflation() -> None:
    resume = _with_experience(bullets=["Led code reviews for the billing team."])
    result = check_inflation(resume, make_facts())
    assert len(result.inflated) == 1
    inflated = result.inflated[0]
    assert (inflated.verb, inflated.verb_level, inflated.scope_ceiling, inflated.fact_id) == (
        "led", 4, 1, "acme_review",
    )
    assert result.rate == 1.0


def test_m2_verb_within_ceiling_is_fine() -> None:
    resume = _with_experience(bullets=["Participated in code reviews for the billing team."])
    assert check_inflation(resume, make_facts()).inflated == []


def test_m2_verb_copied_from_verified_fact_is_grounded() -> None:
    # the fact itself says "Led" and has ceiling 4: no inflation
    resume = _with_experience(
        title="Research Assistant", organization="Beta Labs",
        bullets=["Led a team of 4 students running annotation experiments."],
    )
    assert check_inflation(resume, make_facts()).inflated == []


def test_m2_verbatim_exemption_uses_the_exact_word_not_a_stem() -> None:
    facts = CandidateFacts(facts=[
        AtomicFact(id="pcb", source="experience.acme_corp.bullet_1",
                   text="Participated in custom PCB schematic design and routing.",
                   scope_ceiling=1, tracks=["hardware"]),
    ])
    resume = _with_experience(bullets=["Designed custom PCB schematic and routing."])
    result = check_inflation(resume, facts)
    assert [i.verb for i in result.inflated] == ["designed"]


def test_m2_design_verb_needs_design_evidence_in_the_fact() -> None:
    facts = CandidateFacts(facts=[
        AtomicFact(id="api", source="experience.acme_corp.bullet_1",
                   text="Built REST endpoints for a billing service.", scope_ceiling=3, tracks=["backend"]),
    ])
    resume = _with_experience(bullets=["Architected REST endpoints for a billing service."])
    result = check_inflation(resume, facts)
    assert len(result.inflated) == 1
    assert "design" in result.inflated[0].reason


def test_m2_design_verb_allowed_when_fact_describes_design() -> None:
    facts = CandidateFacts(facts=[
        AtomicFact(id="api", source="experience.acme_corp.bullet_1",
                   text="Designed the REST endpoints of a billing service.", scope_ceiling=3, tracks=["backend"]),
    ])
    resume = _with_experience(bullets=["Architected REST endpoints of a billing service."])
    assert check_inflation(resume, facts).inflated == []


def test_m2_design_verb_with_low_ceiling_is_inflation_even_with_evidence() -> None:
    facts = CandidateFacts(facts=[
        AtomicFact(id="pcb", source="experience.acme_corp.bullet_1",
                   text="Participated in PCB design and routing.", scope_ceiling=1, tracks=["hardware"]),
    ])
    resume = _with_experience(bullets=["Engineered PCB design and routing."])
    assert len(check_inflation(resume, facts).inflated) == 1


def test_m2_unmatched_bullet_is_listed_not_judged() -> None:
    resume = _with_experience(bullets=["Pioneered quantum telepathy for Mars colonies."])
    result = check_inflation(resume, make_facts())
    assert result.inflated == []
    assert result.assessed == 0
    assert result.rate is None
    assert len(result.unmatched) == 1


def test_m2_matched_bullet_with_unknown_lead_verb_is_unranked() -> None:
    resume = _with_experience(bullets=["Awarded recognition for code reviews for the billing team."])
    result = check_inflation(resume, make_facts())
    assert result.inflated == []
    assert len(result.unranked) == 1
    assert result.assessed == 0


def test_m2_resume_without_bullets() -> None:
    resume = make_resume(experiences=[], projects=[])
    result = check_inflation(resume, make_facts())
    assert (result.inflated, result.assessed, result.rate) == ([], 0, None)


# ---------------------------------------------------------------------------
# M3 — coverage
# ---------------------------------------------------------------------------

def test_m3_counts_relevant_facts_by_track_and_priority() -> None:
    result = check_coverage(make_resume(), make_facts(), track="backend")
    # backend facts: acme_api(p1), acme_review(p2), task_api(p1); notes_app is p3/general
    assert result.relevant == ["acme_api", "acme_review", "task_api"]
    assert result.covered == ["acme_api", "acme_review", "task_api"]
    assert result.coverage == 1.0
    assert result.omissions == []


def test_m3_lists_critical_omissions() -> None:
    resume = make_resume(projects=[])
    result = check_coverage(resume, make_facts(), track="backend")
    assert result.omissions == ["task_api"]
    assert result.coverage == pytest.approx(2 / 3)


def test_m3_priority_two_omission_is_not_critical() -> None:
    resume = _with_experience(bullets=["Built REST APIs for an internal billing service using Python and PostgreSQL, cutting report time by 40%."])
    result = check_coverage(resume, make_facts(), track="backend")
    assert "acme_review" not in result.covered
    assert "acme_review" not in result.omissions


def test_m3_track_is_case_insensitive_and_general_is_not_a_match() -> None:
    result = check_coverage(make_resume(), make_facts(), track="BackEnd")
    assert len(result.relevant) == 3
    general = check_coverage(make_resume(), make_facts(), track="general")
    assert general.relevant == []  # notes_app is priority 3


def test_m3_unknown_track_has_no_coverage_value() -> None:
    result = check_coverage(make_resume(), make_facts(), track="quantum")
    assert result.coverage is None
    assert result.omissions == []


def test_m3_max_priority_widens_relevance() -> None:
    result = check_coverage(make_resume(), make_facts(), track="general", max_priority=3)
    assert result.relevant == ["notes_app"]
    assert result.omissions == []  # priority 3 is never a critical omission


def test_m3_fact_covered_by_a_bullet_of_another_entry_does_not_count() -> None:
    # a "billing"-like bullet attached to the wrong employer must not cover the Acme fact
    resume = make_resume(
        experiences=[
            ResumeExperience(
                title="Research Assistant", organization="Beta Labs", period="01/2024 - Present",
                bullets=["Built REST APIs for an internal billing service using Python and PostgreSQL, cutting report time by 40%."],
            )
        ],
        projects=[],
    )
    assert "acme_api" not in check_coverage(resume, make_facts(), track="backend").covered


# ---------------------------------------------------------------------------
# M4 — keywords
# ---------------------------------------------------------------------------

def test_m4_separates_supportable_missing_and_unsupported(truth: GroundTruth) -> None:
    result = check_keywords(make_resume(), make_job(), truth)
    # Job: Python, FastAPI, Kubernetes + REST API, Teamwork
    assert set(result.supportable) == {"Python", "FastAPI", "REST API", "Teamwork"}
    assert set(result.present) == {"Python", "FastAPI", "REST API"}
    assert result.missing == ["Teamwork"]
    assert result.fabricated == []
    assert result.alignment == pytest.approx(3 / 4)


def test_m4_unsupported_keyword_is_excluded_from_denominator(truth: GroundTruth) -> None:
    result = check_keywords(make_resume(), make_job(), truth)
    assert "Kubernetes" not in result.supportable


def test_m4_claiming_an_unsupported_keyword_is_fabrication(truth: GroundTruth) -> None:
    resume = make_resume(skills=[ResumeSkillCategory(category_name="Tools", skills=["Docker", "Kubernetes"])])
    result = check_keywords(resume, make_job(), truth)
    assert result.fabricated == ["Kubernetes"]
    assert result.alignment == pytest.approx(3 / 4)  # fabricating cannot raise alignment


def test_m4_job_without_keywords_has_no_alignment(truth: GroundTruth) -> None:
    result = check_keywords(make_resume(), make_job(technologies=[], keywords=[]), truth)
    assert (result.supportable, result.alignment) == ([], None)


def test_m4_duplicate_and_composite_keywords_are_normalized(truth: GroundTruth) -> None:
    job = make_job(technologies=["Python", "python", "Docker / Git"], keywords=[])
    result = check_keywords(make_resume(), job, truth)
    assert result.supportable == ["Python", "Docker", "Git"]


# ---------------------------------------------------------------------------
# verify_resume
# ---------------------------------------------------------------------------

def test_verify_resume_clean_synthetic_resume_hard_passes() -> None:
    report = verify_resume(
        make_resume(), make_profile(), make_facts(), job=make_job(technologies=["Python"], keywords=[]),
        track="backend",
    )
    assert report.hard_pass, (report.fabrication.unsupported, report.inflation.inflated, report.format.failed)
    assert "one_page" in report.not_verified
    assert "section_titles" in report.not_verified


def test_verify_resume_without_job_and_track_marks_them_not_verified() -> None:
    report = verify_resume(make_resume(), make_profile(), make_facts())
    assert report.coverage is None and report.keywords is None
    assert any("coverage" in name for name in report.not_verified)
    assert any("keywords" in name for name in report.not_verified)


def test_verify_resume_fabricated_keyword_breaks_hard_pass() -> None:
    resume = make_resume(skills=[ResumeSkillCategory(category_name="Tools", skills=["Docker", "Kubernetes"])])
    report = verify_resume(resume, make_profile(), make_facts(), job=make_job())
    assert not report.hard_pass
    assert report.keywords is not None and report.keywords.fabricated == ["Kubernetes"]


def test_verify_resume_inflation_breaks_hard_pass() -> None:
    resume = _with_experience(bullets=["Led code reviews for the billing team."])
    report = verify_resume(resume, make_profile(), make_facts())
    assert not report.hard_pass


def test_verify_resume_allows_digits_of_the_job_title_in_the_summary() -> None:
    resume = make_resume(objective_or_summary="Eager to contribute to backend teams in 2027.")
    job = make_job(title="2027 Backend Software Intern")
    report = verify_resume(resume, make_profile(), make_facts(), job=job)
    assert report.fabrication.unsupported_of("b") == []
    plain = verify_resume(resume, make_profile(), make_facts(), job=make_job())
    assert [c.text for c in plain.fabrication.unsupported_of("b")] == ["2027"]
