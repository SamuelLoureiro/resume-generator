"""Unit tests for the seeded synthetic lie injection harness.

Validates that:
- Injections are deterministic and reproducible under fixed seeds.
- Defect classes L1, L2, L3, L4 trigger their intended deterministic M1a-c / M2 checks.
- L5 (Evidence Ablation) and L6 (Cross-Project Conflation) produce valid ledger records.
"""

from __future__ import annotations

from src.data.synthetic_profiles import get_synthetic_fresh_grad, get_synthetic_researcher
from src.data.job_posting import JobPosting
from src.evaluation.injection import (
    _stable_rng,
    generate_corrupted_dataset,
    inject_cross_project_conflation,
    inject_fabricated_responsibility_ablation,
    inject_fake_entity_date,
    inject_fake_number,
    inject_fake_skill,
    inject_fused_facts,
    inject_inflated_verb,
    inject_job_phrase_echo,
    inject_meta_word,
)
from src.generation.chain import build_fallback_tailored_resume
from src.verification.ground_truth import GroundTruth
from src.verification.report import verify_resume


def _make_sample_resume():
    profile, facts = get_synthetic_fresh_grad()
    job = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Software Engineering Intern at TechCorp requiring Python and C++.",
        track="core_swe",
        technologies=["Python", "C++", "Linux", "Docker"],
        keywords=["algorithms", "data structures", "distributed systems"],
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")
    return resume, profile, facts, job


def test_stable_rng_determinism() -> None:
    rng1 = _stable_rng(42, "resume_1", "fake_skill")
    rng2 = _stable_rng(42, "resume_1", "fake_skill")
    rng3 = _stable_rng(99, "resume_1", "fake_skill")

    val1 = [rng1.random() for _ in range(5)]
    val2 = [rng2.random() for _ in range(5)]
    val3 = [rng3.random() for _ in range(5)]

    assert val1 == val2
    assert val1 != val3


def test_inject_fake_skill_triggers_m1a() -> None:
    resume, profile, facts, job = _make_sample_resume()
    truth = GroundTruth(profile, facts)

    mut_resume, injection = inject_fake_skill(resume, truth, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "fake_skill"
    assert injection.expected_detector == "deterministic_p5"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    # M1a must detect the injected fake skill
    unsupported_skills = report.fabrication.unsupported_of("a")
    assert len(unsupported_skills) >= 1
    assert any(injection.injected_span in c.text for c in unsupported_skills)
    assert not report.hard_pass


def test_inject_fake_number_triggers_m1b() -> None:
    resume, profile, facts, job = _make_sample_resume()
    truth = GroundTruth(profile, facts)

    mut_resume, injection = inject_fake_number(resume, truth, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "fake_number"
    assert injection.expected_detector == "deterministic_p5"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    # M1b must detect the unverified number
    unsupported_numbers = report.fabrication.unsupported_of("b")
    assert len(unsupported_numbers) >= 1
    assert not report.hard_pass


def test_inject_inflated_verb_triggers_m2() -> None:
    # Use synthetic researcher who has facts with scope ceiling <= 3
    profile, facts = get_synthetic_researcher()
    job = JobPosting(
        title="Machine Learning Research Intern",
        company="AI Research Lab",
        raw_description="Machine Learning Research Intern at AI Research Lab.",
        track="ai",
        technologies=["Python", "PyTorch"],
        keywords=["deep learning"],
    )
    resume = build_fallback_tailored_resume(profile, job, language="en")

    # Force a fact to ceiling 2 to test inflation
    facts.facts[1].scope_ceiling = 2

    mut_resume, injection = inject_inflated_verb(resume, facts, seed=42, resume_id="test_researcher")
    assert injection.defect_class == "inflated_verb"
    assert injection.expected_detector == "deterministic_p5"

    report = verify_resume(mut_resume, profile, facts, job=job, track="ai")
    assert len(report.inflation.inflated) >= 1
    assert any(i.verb.lower() == injection.injected_span.lower() for i in report.inflation.inflated)
    assert not report.hard_pass


def test_inject_fake_entity_date_triggers_m1c() -> None:
    resume, profile, facts, job = _make_sample_resume()

    mut_resume, injection = inject_fake_entity_date(resume, profile, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "fake_entity_date"
    assert injection.expected_detector == "deterministic_p5"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    unsupported_entities = report.fabrication.unsupported_of("c")
    assert len(unsupported_entities) >= 1
    assert not report.hard_pass


def test_inject_fabricated_responsibility_ablation() -> None:
    resume, profile, facts, job = _make_sample_resume()

    mut_resume, active_facts, injection = inject_fabricated_responsibility_ablation(
        resume, facts, seed=42, resume_id="test_fresh_grad"
    )
    assert injection.defect_class == "fabricated_responsibility"
    assert injection.expected_detector == "claim_judge_llm"
    assert injection.ablated_fact_id is not None
    assert len(active_facts.facts) == len(facts.facts) - 1

    # Wording is 100% genuine candidate text
    assert mut_resume == resume


def test_inject_cross_project_conflation() -> None:
    resume, profile, facts, job = _make_sample_resume()

    mut_resume, injection = inject_cross_project_conflation(
        resume, facts, seed=42, resume_id="test_fresh_grad"
    )
    assert injection.defect_class == "cross_project_conflation"
    assert injection.expected_detector == "claim_judge_llm"
    assert injection.injected_span in injection.injected_text


def test_inject_meta_word_triggers_b1() -> None:
    resume, profile, facts, job = _make_sample_resume()
    mut_resume, injection = inject_meta_word(resume, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "meta_word"
    assert injection.expected_detector == "deterministic_p5"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    assert not report.defect_free
    assert any(d["kind"] == "summary_lint" and "verified" in d["text"] for d in report.defects)


def test_inject_job_phrase_echo_triggers_b2() -> None:
    resume, profile, facts, job = _make_sample_resume()
    # Ensure job description has the phrase
    job.raw_description = "Develop lightweight neural networks for edge devices."
    mut_resume, injection = inject_job_phrase_echo(resume, job, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "job_phrase_echo"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    assert not report.defect_free
    assert any(d["kind"] == "job_phrase_echo" and "lightweight neural networks" in d["text"] for d in report.defects)


def test_inject_fused_facts_triggers_b3() -> None:
    resume, profile, facts, job = _make_sample_resume()
    mut_resume, injection = inject_fused_facts(resume, seed=42, resume_id="test_fresh_grad")
    assert injection.defect_class == "fused_facts"

    report = verify_resume(mut_resume, profile, facts, job=job, track="core_swe")
    assert not report.defect_free
    assert any(d["kind"] == "fact_fusion" for d in report.defects)


def test_generate_corrupted_dataset_summary() -> None:
    profile_a, facts_a = get_synthetic_fresh_grad()
    job_a = JobPosting(
        title="Software Engineering Intern",
        company="TechCorp",
        raw_description="Develop lightweight neural networks for embedded systems.",
        track="core_swe",
    )
    resume_a = build_fallback_tailored_resume(profile_a, job_a, language="en")

    clean_resumes = {"grad_a": resume_a}
    profiles = {"grad_a": profile_a}
    facts_map = {"grad_a": facts_a}

    corrupted_list, ledger = generate_corrupted_dataset(clean_resumes, profiles, facts_map, seed=42)
    assert len(corrupted_list) >= 4
    assert len(ledger) == len(corrupted_list)

    defect_classes = {inj.defect_class for inj in ledger}
    assert "fake_skill" in defect_classes
    assert "fake_number" in defect_classes
    assert "fabricated_responsibility" in defect_classes
    assert "meta_word" in defect_classes
    assert "job_phrase_echo" in defect_classes
    assert "fused_facts" in defect_classes
