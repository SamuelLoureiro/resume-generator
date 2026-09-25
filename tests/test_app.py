"""Unit tests for the Gradio web application layout and handlers in src/app.py."""

from __future__ import annotations

from pathlib import Path
import pytest
import gradio as gr

from src.app import (
    build_app,
    handle_profile_upload,
    load_candidate_profile_from_path,
)
from src.data.candidate import CandidateProfile, ContactInfo, Education, Skills


def test_load_candidate_profile_from_path_default() -> None:
    """Test loading the default candidate profile YAML."""
    default_path = Path("data/candidate_profile.yaml")
    profile, summary_md = load_candidate_profile_from_path(default_path)

    assert isinstance(profile, CandidateProfile)
    assert profile.contact.full_name is not None
    assert profile.contact.full_name in summary_md
    assert "Active Candidate Profile:" in summary_md


def test_load_candidate_profile_from_path_missing_raises(tmp_path: Path) -> None:
    """Test that pointing to a missing profile file raises FileNotFoundError."""
    missing_path = tmp_path / "missing.yaml"
    with pytest.raises(FileNotFoundError):
        load_candidate_profile_from_path(missing_path)


def test_handle_profile_upload_none() -> None:
    """Test that uploading None reverts cleanly to the default profile."""
    status, summary_md = handle_profile_upload(None)
    assert "Reverted to default" in status
    assert "Active Candidate Profile:" in summary_md


def test_handle_profile_upload_custom_valid(tmp_path: Path) -> None:
    """Test uploading a valid custom candidate YAML file."""
    custom_profile = CandidateProfile(
        contact=ContactInfo(
            full_name="Ana Costa",
            email="ana@example.com",
            phone="+55 11 91234-5678",
            location="Campinas, SP",
        ),
        education=[
            Education(
                institution="Unicamp",
                degree="Computer Engineering",
                start_date="2022",
                end_date="2026",
            )
        ],
    )
    custom_path = tmp_path / "custom_candidate.yaml"
    custom_profile.to_yaml(custom_path)

    status, summary_md = handle_profile_upload(custom_path)
    assert "Successfully loaded custom profile" in status
    assert "Ana Costa" in summary_md


def test_handle_profile_upload_invalid(tmp_path: Path) -> None:
    """Test uploading a malformed file returns an error message gracefully."""
    invalid_file = tmp_path / "bad.yaml"
    invalid_file.write_text("invalid_yaml: [missing_brace", encoding="utf-8")

    status, summary_md = handle_profile_upload(invalid_file)
    assert "Invalid candidate YAML" in status
    assert "Error in uploaded file" in summary_md


def test_build_app_structure() -> None:
    """Test that build_app successfully constructs the Gradio Blocks application."""
    app = build_app()
    assert isinstance(app, gr.Blocks)
