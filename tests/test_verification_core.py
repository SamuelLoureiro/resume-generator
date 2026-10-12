"""Unit tests for the shared building blocks of src/verification (offline)."""

from __future__ import annotations

import pytest

from src.verification.ground_truth import GroundTruth, extract_numbers
from src.verification.matching import (
    BulletRef,
    candidate_facts_for,
    extract_bullets,
    match_bullet,
    match_resume_bullets,
)
from src.verification.text_utils import (
    ngram_keys,
    similarity,
    split_terms,
    term_key,
    term_keys,
    tokenize,
    unescape_latex,
)
from src.verification.verb_ladder import design_evidence_in, extract_lead_verb
from src.data.resume import escape_latex
from tests.verification_data import make_facts, make_profile, make_resume


# ---------------------------------------------------------------------------
# text_utils
# ---------------------------------------------------------------------------

def test_term_key_ignores_separators_case_and_plural() -> None:
    assert term_key("Scikit-Learn") == term_key("scikit learn") == term_key("SCIKITLEARN")
    assert term_key("ROS 2") == term_key("ros2")
    assert term_key("REST APIs") == term_key("rest-api")


def test_term_key_keeps_plus_and_hash() -> None:
    assert term_key("C++") != term_key("C")
    assert term_key("C#") != term_key("C")


def test_split_terms_handles_composites() -> None:
    assert split_terms("Python (Pandas, NumPy)") == ["Python", "Pandas", "NumPy"]
    assert split_terms("C / C++") == ["C", "C++"]
    assert split_terms("SPI / UART / I2C / PIO") == ["SPI", "UART", "I2C", "PIO"]
    assert split_terms("") == []


def test_term_keys_skips_empty_parts() -> None:
    assert term_keys(["Git / GitHub", " "]) == {"git", "github"}


def test_ngram_keys_locates_multiword_terms() -> None:
    keys = ngram_keys("Deployed REST APIs on ROS 2 robots")
    assert term_key("REST API") in keys
    assert term_key("ROS 2") in keys
    assert term_key("graph theory") not in keys


def test_tokenize_empty_and_none_like() -> None:
    assert tokenize("") == []
    assert tokenize(None) == []  # type: ignore[arg-type]


def test_similarity_bounds_and_symmetry() -> None:
    a = "Built REST endpoints for a billing service"
    b = "Built REST APIs for a billing service"
    assert similarity(a, a) == pytest.approx(1.0)
    assert similarity(a, b) == pytest.approx(similarity(b, a))
    assert 0.0 < similarity(a, b) < 1.0
    assert similarity(a, "") == 0.0
    assert similarity("", "") == 0.0
    assert similarity(a, "quantum entanglement of photons") == 0.0


def test_unescape_latex_inverts_escape_latex() -> None:
    original = "R&D at 50% cost, C_1 #1 {x} ~ ^ — end"
    assert unescape_latex(escape_latex(original)) == original


# ---------------------------------------------------------------------------
# verb ladder
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("bullet", "phrase", "level", "is_design"),
    [
        ("Participated in custom PCB design", "participated in", 1, False),
        ("Took part in a hackathon", "took part in", 1, False),
        ("Contributed to the billing service", "contributed to", 2, False),
        ("Co-designed a sensor board", "co-designed", 2, False),
        ("Helped build a dashboard", "helped build", 2, False),
        ("Developed a REST API", "developed", 3, False),
        ("Integrated an IMU via I2C", "integrated", 3, False),
        ("Led a team of 5 developers", "led", 4, False),
        ("Managed and developed apps", "managed", 4, False),
        ("Spearheaded the new department", "spearheaded", 4, False),
        ("Architected a pipeline", "architected", 3, True),
        ("Engineered firmware", "engineered", 3, True),
        ("Designed multilayer PCBs", "designed", 3, True),
        ("Dirigé une équipe de cinq personnes", "dirigé", 4, False),
        ("Desenvolveu uma API REST", "desenvolveu", 3, False),
        ("Participou de um projeto", "participou de", 1, False),
    ],
)
def test_extract_lead_verb(bullet: str, phrase: str, level: int, is_design: bool) -> None:
    lead = extract_lead_verb(bullet)
    assert lead is not None
    assert (lead.phrase, lead.level, lead.is_design) == (phrase, level, is_design)


def test_extract_lead_verb_skips_leading_adverb() -> None:
    lead = extract_lead_verb("Successfully led the migration")
    assert lead is not None and lead.level == 4


@pytest.mark.parametrize("bullet", ["", "   ", "Awarded Member of the Month", "2023 internship", "Promoted to manager"])
def test_extract_lead_verb_unknown_returns_none(bullet: str) -> None:
    assert extract_lead_verb(bullet) is None


def test_design_evidence() -> None:
    assert design_evidence_in("Participated in custom PCB schematic design")
    assert design_evidence_in("Engineered real-time C firmware")
    assert not design_evidence_in("Delivered commercial data processing automation")
    assert not design_evidence_in("")


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Improved accuracy to 80% and cut cost by 5+ points", ["80%", "5+"]),
        ("Processed 50,000 articles", ["50000"]),
        ("MPU9250 over I2C on RP2350", []),
        ("Raspberry Pi Pico 2 with ROS 2", ["2", "2"]),
        ("Period 09/2025 - 12/2025", []),
        ("Version 3.5 release", ["3.5"]),
        ("", []),
    ],
)
def test_extract_numbers(text: str, expected: list[str]) -> None:
    assert extract_numbers(text) == expected


def test_skill_allowlist_accepts_composites_plurals_and_hyphens() -> None:
    truth = GroundTruth(make_profile(), make_facts())
    assert truth.is_allowed_skill("C / C++")
    assert truth.is_allowed_skill("Git / GitHub")
    assert truth.is_allowed_skill("Scikit Learn")
    assert truth.is_allowed_skill("REST APIs")  # from fact tag rest-api
    assert truth.is_allowed_skill("python")


def test_skill_allowlist_rejects_unknown_terms_even_inside_composites() -> None:
    truth = GroundTruth(make_profile(), make_facts())
    assert not truth.is_allowed_skill("Kubernetes")
    assert not truth.is_allowed_skill("Python (Pandas)")
    assert not truth.is_allowed_skill("C / Rust")


def test_number_support_rules() -> None:
    truth = GroundTruth(make_profile(), make_facts())
    assert truth.is_supported_number("40%")
    assert truth.is_supported_number("4")
    assert not truth.is_supported_number("4+")  # suffix never verified
    assert not truth.is_supported_number("60%")
    assert not truth.is_supported_number("40+")
    assert truth.is_supported_number("2023")  # year from a profile date
    assert truth.is_supported_number("9", extra_allowed={"9"})


def test_contact_digits_never_support_numbers() -> None:
    truth = GroundTruth(make_profile(), make_facts())
    # the invented phone is +33 7 11 22 33 44: 7, 11, 22, 33, 44 must not leak in
    for token in ("7", "11", "22", "33", "44"):
        assert not truth.is_supported_number(token), token


def test_has_term_uses_skills_and_verified_text() -> None:
    truth = GroundTruth(make_profile(), make_facts())
    assert truth.has_term("Python")
    assert truth.has_term("billing service")  # phrase from a fact, not a skill
    assert truth.has_term("code reviews")
    assert not truth.has_term("Kubernetes")
    assert not truth.has_term("")


# ---------------------------------------------------------------------------
# matching
# ---------------------------------------------------------------------------

def test_extract_bullets_covers_experiences_and_projects() -> None:
    refs = extract_bullets(make_resume())
    kinds = [r.kind for r in refs]
    assert kinds.count("experience") == 3
    assert kinds.count("project") == 1
    assert refs[0].entry.startswith("Acme Corp")


def test_candidate_facts_restricted_to_recognised_entry() -> None:
    facts = make_facts()
    ref = BulletRef("anything", "experience", "Acme Corp Backend Intern")
    ids = {f.id for f in candidate_facts_for(ref, facts)}
    assert ids == {"acme_api", "acme_review"}


def test_candidate_facts_fall_back_to_all_when_entry_unknown() -> None:
    facts = make_facts()
    ref = BulletRef("anything", "experience", "Gamma Inc Wizard")
    assert len(candidate_facts_for(ref, facts)) == len(facts)


def test_match_bullet_picks_nearest_fact_inside_entry() -> None:
    facts = make_facts()
    ref = BulletRef("Participated in code reviews for the billing team.", "experience", "Acme Corp Backend Intern")
    match = match_bullet(ref, facts)
    assert match.fact_id == "acme_review"
    assert match.score == pytest.approx(1.0)


def test_match_bullet_below_threshold_is_unmatched_but_reports_best() -> None:
    facts = make_facts()
    ref = BulletRef("Optimized billing databases for Mars rovers", "experience", "Acme Corp Backend Intern")
    match = match_bullet(ref, facts)
    assert match.fact_id is None
    assert match.best_fact_id in {"acme_api", "acme_review"}  # only the Acme entry's facts compete
    assert 0.0 < match.score < 0.30


def test_match_bullet_without_any_overlap_has_no_candidate() -> None:
    ref = BulletRef("Optimized quantum photons for Mars rovers", "experience", "Acme Corp Backend Intern")
    match = match_bullet(ref, make_facts())
    assert (match.fact_id, match.best_fact_id, match.score) == (None, None, 0.0)


def test_match_resume_bullets_clean_resume_all_matched() -> None:
    matches = match_resume_bullets(make_resume(), make_facts())
    assert [m.fact_id for m in matches] == ["acme_api", "acme_review", "beta_lead", "task_api"]


def test_match_with_no_facts_is_unmatched_not_a_crash() -> None:
    from src.data.facts import CandidateFacts

    matches = match_resume_bullets(make_resume(), CandidateFacts(facts=[]))
    assert matches and all(m.fact_id is None and m.best_fact_id is None for m in matches)
