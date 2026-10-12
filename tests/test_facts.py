"""Unit tests for AtomicFact, CandidateFacts, and load_candidate_facts."""

from __future__ import annotations

from pathlib import Path
import pytest
import yaml

from src.data.facts import (
    SCOPE_LEVEL_NAMES,
    AtomicFact,
    CandidateFacts,
    load_candidate_facts,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_atomic_fact() -> AtomicFact:
    """Fixture providing a valid AtomicFact."""
    return AtomicFact(
        id="exp_asimov_leadership",
        source="experience.asimov_jr.bullet_1",
        text="Promoted to Mobile Area Manager, leading 5+ developers and founding the Data Science area.",
        scope_ceiling=4,
        tracks=["backend", "ai", "data"],
        priority=1,
        metrics=["5+ developers"],
        tags=["leadership", "management", "mobile", "data-science"],
    )


@pytest.fixture
def sample_candidate_facts(sample_atomic_fact: AtomicFact) -> CandidateFacts:
    """Fixture providing a CandidateFacts collection."""
    fact2 = AtomicFact(
        id="exp_asimov_mobile_dev",
        source="experience.asimov_jr.bullet_2",
        text="Managed and developed cross-platform mobile applications using Flutter and MongoDB.",
        scope_ceiling=3,
        tracks=["backend", "core_swe"],
        priority=2,
        metrics=[],
        tags=["flutter", "dart", "mongodb", "rest-api"],
    )
    fact3 = AtomicFact(
        id="exp_enib_pcb",
        source="experience.enib.bullet_2",
        text="Participated in custom PCB schematic design and routing using EasyEDA.",
        scope_ceiling=1,
        tracks=["embedded"],
        priority=3,
        metrics=[],
        tags=["pcb", "easyeda", "hardware"],
    )
    return CandidateFacts(facts=[sample_atomic_fact, fact2, fact3])


# ---------------------------------------------------------------------------
# AtomicFact Schema Tests
# ---------------------------------------------------------------------------

def test_atomic_fact_valid(sample_atomic_fact: AtomicFact) -> None:
    """Test valid instantiation and field properties of AtomicFact."""
    assert sample_atomic_fact.id == "exp_asimov_leadership"
    assert sample_atomic_fact.scope_ceiling == 4
    assert sample_atomic_fact.scope_name == "led"
    assert "5+ developers" in sample_atomic_fact.metrics
    assert "leadership" in sample_atomic_fact.tags


@pytest.mark.parametrize("invalid_ceiling", [0, 5, -1, 10])
def test_atomic_fact_invalid_scope_ceiling(invalid_ceiling: int) -> None:
    """Test that scope_ceiling outside [1, 4] raises ValidationError."""
    with pytest.raises(ValueError):
        AtomicFact(
            id="fact_invalid_scope",
            source="experience.item",
            text="Invalid scope test",
            scope_ceiling=invalid_ceiling,
        )


@pytest.mark.parametrize("invalid_priority", [0, 4, -2, 99])
def test_atomic_fact_invalid_priority(invalid_priority: int) -> None:
    """Test that priority outside [1, 3] raises ValidationError."""
    with pytest.raises(ValueError):
        AtomicFact(
            id="fact_invalid_priority",
            source="experience.item",
            text="Invalid priority test",
            scope_ceiling=3,
            priority=invalid_priority,
        )


def test_scope_ladder_descriptions() -> None:
    """Test that all 4 scope levels have designated descriptive names."""
    assert SCOPE_LEVEL_NAMES[1] == "participated"
    assert SCOPE_LEVEL_NAMES[2] == "contributed"
    assert SCOPE_LEVEL_NAMES[3] == "developed"
    assert SCOPE_LEVEL_NAMES[4] == "led"


# ---------------------------------------------------------------------------
# CandidateFacts Collection Tests
# ---------------------------------------------------------------------------

def test_candidate_facts_duplicate_id_raises(sample_atomic_fact: AtomicFact) -> None:
    """Test that duplicate fact IDs within a collection raise ValueError."""
    dup_fact = AtomicFact(
        id=sample_atomic_fact.id,  # Duplicate ID
        source="another.source",
        text="Duplicate claim",
        scope_ceiling=2,
    )
    with pytest.raises(ValueError, match="Duplicate atomic fact IDs found"):
        CandidateFacts(facts=[sample_atomic_fact, dup_fact])


def test_candidate_facts_get_by_id(sample_candidate_facts: CandidateFacts) -> None:
    """Test retrieving facts by ID."""
    found = sample_candidate_facts.get_by_id("exp_asimov_leadership")
    assert found is not None
    assert found.scope_ceiling == 4

    missing = sample_candidate_facts.get_by_id("non_existent_id")
    assert missing is None


def test_candidate_facts_filter_by_track(sample_candidate_facts: CandidateFacts) -> None:
    """Test filtering facts by job track."""
    backend_facts = sample_candidate_facts.filter_by_track("backend")
    assert len(backend_facts) == 2
    assert all("backend" in f.tracks for f in backend_facts)

    embedded_facts = sample_candidate_facts.filter_by_track("embedded")
    assert len(embedded_facts) == 1
    assert embedded_facts[0].id == "exp_enib_pcb"

    empty_facts = sample_candidate_facts.filter_by_track("unrelated_track")
    assert len(empty_facts) == 0


def test_candidate_facts_filter_by_priority(sample_candidate_facts: CandidateFacts) -> None:
    """Test filtering facts by priority threshold."""
    # Priority <= 1 should return only priority 1
    p1 = sample_candidate_facts.filter_by_priority(1)
    assert len(p1) == 1
    assert p1[0].priority == 1

    # Priority <= 2 should return priority 1 and 2
    p2 = sample_candidate_facts.filter_by_priority(2)
    assert len(p2) == 2

    # Priority <= 3 should return all 3
    p3 = sample_candidate_facts.filter_by_priority(3)
    assert len(p3) == 3


def test_candidate_facts_metrics_and_tags(sample_candidate_facts: CandidateFacts) -> None:
    """Test extracting allowed metrics and technology tags."""
    metrics = sample_candidate_facts.get_allowed_metrics()
    assert "5+ developers" in metrics

    tags = sample_candidate_facts.get_allowed_tags()
    assert "flutter" in tags
    assert "leadership" in tags
    assert "pcb" in tags
    assert len(sample_candidate_facts) == 3


# ---------------------------------------------------------------------------
# Loader Tests
# ---------------------------------------------------------------------------

def test_load_candidate_facts_valid_dict(tmp_path: Path) -> None:
    """Test loading valid YAML containing a 'facts' root key."""
    data = {
        "facts": [
            {
                "id": "fact_1",
                "source": "experience.1",
                "text": "Engineered real-time firmware in C.",
                "scope_ceiling": 3,
                "tracks": ["embedded"],
                "priority": 1,
                "metrics": ["100 Hz"],
                "tags": ["c", "firmware"],
            }
        ]
    }
    file_path = tmp_path / "facts.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loaded = load_candidate_facts(file_path)
    assert len(loaded) == 1
    assert loaded.facts[0].id == "fact_1"
    assert loaded.facts[0].scope_ceiling == 3


def test_load_candidate_facts_valid_list(tmp_path: Path) -> None:
    """Test loading valid YAML structured as a raw list of facts."""
    data = [
        {
            "id": "fact_list_1",
            "source": "project.1",
            "text": "Trained TinyML models achieving 80% accuracy.",
            "scope_ceiling": 3,
            "tracks": ["ai", "embedded"],
            "priority": 1,
            "metrics": ["80% accuracy"],
            "tags": ["tinyml", "edge-impulse"],
        }
    ]
    file_path = tmp_path / "facts_list.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    loaded = load_candidate_facts(file_path)
    assert len(loaded) == 1
    assert loaded.facts[0].id == "fact_list_1"


def test_load_candidate_facts_empty_file(tmp_path: Path) -> None:
    """Test loading an empty YAML file returns an empty CandidateFacts collection."""
    file_path = tmp_path / "empty.yaml"
    file_path.write_text("", encoding="utf-8")

    loaded = load_candidate_facts(file_path)
    assert len(loaded) == 0


def test_load_candidate_facts_file_not_found() -> None:
    """Test that non-existent facts file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError, match="Candidate facts file not found"):
        load_candidate_facts(Path("/non/existent/path/facts.yaml"))


def test_load_candidate_facts_invalid_yaml(tmp_path: Path) -> None:
    """Test that syntax errors in YAML raise ValueError."""
    file_path = tmp_path / "bad_syntax.yaml"
    file_path.write_text("facts: [unclosed list", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed YAML"):
        load_candidate_facts(file_path)


def test_load_candidate_facts_schema_violation(tmp_path: Path) -> None:
    """Test that schema validation failure raises ValueError."""
    data = {
        "facts": [
            {
                "id": "invalid_fact",
                "source": "experience.1",
                "text": "Missing scope ceiling",
                # missing required scope_ceiling
            }
        ]
    }
    file_path = tmp_path / "schema_error.yaml"
    file_path.write_text(yaml.safe_dump(data), encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid candidate facts schema"):
        load_candidate_facts(file_path)


def test_load_actual_candidate_facts_yaml() -> None:
    """Test that the project's data/candidate_facts.yaml loads cleanly and passes all constraints."""
    facts = load_candidate_facts()
    assert len(facts) >= 10, "Expected at least 10 verified atomic facts in candidate_facts.yaml"
    assert facts.get_by_id("exp_asimov_leadership") is not None
    assert facts.get_by_id("exp_enib_pcb_design") is not None
    assert facts.get_by_id("proj_rag_resume_engine") is not None

    # Verify metrics extraction
    allowed_metrics = facts.get_allowed_metrics()
    assert "5+ developers" in allowed_metrics
    assert "80% accuracy" in allowed_metrics

    # Verify every fact is well-formed
    for fact in facts.facts:
        assert 1 <= fact.scope_ceiling <= 4
        assert 1 <= fact.priority <= 3
        assert fact.id.strip() != ""
        assert fact.text.strip() != ""
        assert len(fact.tracks) > 0
