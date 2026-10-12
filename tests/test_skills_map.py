"""Unit tests for deterministic skills category mapping and taxonomy."""

from __future__ import annotations

from pathlib import Path
import pytest

from src.data.candidate import CandidateProfile
from src.data.resume import ResumeSkillCategory
from src.data.skills_map import (
    CATEGORY_NAMES,
    flag_unknown_skills,
    get_skill_category_key,
    get_skill_category_name,
    reorganize_resume_skills,
)


def test_ros2_mapped_to_robotics_and_middleware() -> None:
    """Verify that ROS 2 and robotics variants map to robotics category in all languages."""
    assert get_skill_category_key("ROS 2") == "robotics"
    assert get_skill_category_key("ROS2") == "robotics"
    assert get_skill_category_key("ROS") == "robotics"
    assert get_skill_category_key("Micro-ROS") == "robotics"

    # Check localized names
    assert get_skill_category_name("ROS 2", "en") == "Robotics & Middleware"
    assert get_skill_category_name("ROS 2", "pt") == "Robótica & Middleware"
    assert get_skill_category_name("ROS 2", "fr") == "Robotique & Middleware"


def test_reorganize_moves_ros2_out_of_frameworks() -> None:
    """Test that reorganize_resume_skills moves ROS 2 from Frameworks into Robotics."""
    misplaced_categories = [
        ResumeSkillCategory(
            category_name="Programming Languages",
            skills=["Python", "C++"],
        ),
        ResumeSkillCategory(
            category_name="Frameworks & Machine Learning",
            skills=["PyTorch", "TensorFlow", "ROS 2", "Scikit-Learn"],
        ),
        ResumeSkillCategory(
            category_name="Tools & Platforms",
            skills=["Git", "Docker"],
        ),
    ]

    reorganized = reorganize_resume_skills(misplaced_categories, language="en")
    by_name = {cat.category_name: cat.skills for cat in reorganized}

    # ROS 2 must NOT be in Frameworks
    assert "ROS 2" not in by_name["Frameworks and Libraries"]
    assert "PyTorch" in by_name["Frameworks and Libraries"]
    assert "TensorFlow" in by_name["Frameworks and Libraries"]

    # ROS 2 must be in Robotics & Middleware
    assert "Robotics & Middleware" in by_name
    assert by_name["Robotics & Middleware"] == ["ROS 2"]

    # Programming Languages and Tools must remain intact
    assert by_name["Programming Languages"] == ["Python", "C++"]
    assert by_name["Tools and Platforms"] == ["Git", "Docker"]


def test_all_candidate_profile_skills_mapped() -> None:
    """Assert each skill in the verified candidate profile sits in its expected mapped category."""
    profile_path = Path(__file__).resolve().parent.parent / "data" / "candidate_profile.yaml"
    profile = CandidateProfile.from_yaml(profile_path)

    # 1. Programming languages -> prog
    for s in profile.skills.programming_languages:
        assert get_skill_category_key(s) == "prog", f"Skill '{s}' not mapped to prog"

    # 2. Frameworks and libraries -> frameworks
    for s in profile.skills.frameworks_and_libraries:
        assert get_skill_category_key(s) == "frameworks", f"Skill '{s}' not mapped to frameworks"

    # 3. Databases -> databases
    for s in profile.skills.databases:
        assert get_skill_category_key(s) == "databases", f"Skill '{s}' not mapped to databases"

    # 4. Tools and platforms
    for s in profile.skills.tools_and_platforms:
        if s in ("ROS 2", "ROS"):
            assert get_skill_category_key(s) == "robotics", f"ROS 2 must map to robotics, got: {get_skill_category_key(s)}"
        elif s in ("FreeRTOS", "CAN Bus / I2C / SPI"):
            assert get_skill_category_key(s) == "embedded", f"Skill '{s}' must map to embedded"
        else:
            assert get_skill_category_key(s) == "tools", f"Skill '{s}' must map to tools"

    # 5. Soft skills -> soft
    for s in profile.skills.soft_skills:
        assert get_skill_category_key(s) == "soft", f"Skill '{s}' not mapped to soft"

    # 6. Flag unknown skills on all profile skills returns empty list
    all_skills = (
        profile.skills.programming_languages
        + profile.skills.frameworks_and_libraries
        + profile.skills.databases
        + profile.skills.tools_and_platforms
        + profile.skills.soft_skills
    )
    unknowns = flag_unknown_skills(all_skills)
    assert unknowns == [], f"Found unknown skills in candidate profile: {unknowns}"


def test_flag_unknown_skills() -> None:
    """Verify that unmapped skills are accurately flagged as unknown."""
    skills = ["Python", "ROS 2", "PyTorch", "QuantumSuperComputing", "HologramSynthesis"]
    unknowns = flag_unknown_skills(skills)
    assert unknowns == ["QuantumSuperComputing", "HologramSynthesis"]


def test_reorganize_resume_skills_multilingual() -> None:
    """Verify reorganization produces localized category names for French and Portuguese."""
    raw_cats = [
        {"category_name": "Tech", "skills": ["Python", "ROS 2", "FreeRTOS", "MongoDB"]},
    ]

    reorg_pt = reorganize_resume_skills(raw_cats, language="pt")
    pt_names = [c.category_name for c in reorg_pt]
    assert "Linguagens de Programação" in pt_names
    assert "Sistemas Embarcados & Comunicação" in pt_names
    assert "Robótica & Middleware" in pt_names
    assert "Bancos de Dados" in pt_names

    reorg_fr = reorganize_resume_skills(raw_cats, language="fr")
    fr_names = [c.category_name for c in reorg_fr]
    assert "Langages de programmation" in fr_names
    assert "Systèmes embarqués & Communication" in fr_names
    assert "Robotique & Middleware" in fr_names
    assert "Bases de données" in fr_names
