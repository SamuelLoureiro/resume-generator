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


# ---------------------------------------------------------------------------
# generate_resume_action tests
# ---------------------------------------------------------------------------

def test_generate_resume_action_missing_inputs() -> None:
    """Test that missing mandatory fields return clear user warnings."""
    from src.app import generate_resume_action

    # Missing job title
    status, pdf, info, guide, tex = generate_resume_action(
        uploaded_file=None,
        job_title="",
        company="Google",
        location="",
        work_model="Hybrid",
        job_description="Description here",
        technologies="",
    )
    assert "Missing Field" in status
    assert "Job Title" in status
    assert pdf is None

    # Missing company
    status, pdf, info, guide, tex = generate_resume_action(
        uploaded_file=None,
        job_title="ML Intern",
        company="",
        location="",
        work_model="Hybrid",
        job_description="Description here",
        technologies="",
    )
    assert "Missing Field" in status
    assert "Hiring Company" in status
    assert pdf is None

    # Missing description
    status, pdf, info, guide, tex = generate_resume_action(
        uploaded_file=None,
        job_title="ML Intern",
        company="Google",
        location="",
        work_model="Hybrid",
        job_description="",
        technologies="",
    )
    assert "Missing Field" in status
    assert "Job Description" in status
    assert pdf is None


def test_generate_resume_action_with_mocks(tmp_path: Path) -> None:
    """Test full generate_resume_action workflow using injected mocks."""
    from unittest.mock import MagicMock
    from src.app import generate_resume_action
    from src.data.resume import ResumeHeader, TailoredResume

    # Mock pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "### [Guideline 1: XYZ Formula]\nQuantify results."

    # Mock tailored resume
    mock_resume = TailoredResume(
        target_job_title="ML Intern",
        target_company="DeepMind",
        header=ResumeHeader(
            full_name="Samuel Silva",
            email="samuel@example.com",
            phone="+55 11 99999-9999",
            location="São Paulo, SP",
        ),
        objective_or_summary="Student focused on ML and RAG systems.",
    )

    # Mock chain
    mock_chain = MagicMock()
    mock_chain.generate.return_value = mock_resume

    # Mock formatter & fake compiled PDF
    fake_pdf = tmp_path / "test_resume.pdf"
    fake_pdf.write_bytes(b"%PDF-1.5 fake pdf content for test")

    mock_formatter = MagicMock()
    mock_formatter.render_latex.return_value = "\\documentclass{article}\\begin{document}Hello\\end{document}"
    mock_formatter.compile_pdf.return_value = fake_pdf

    status, pdf_path, info_md, guidelines, rendered_tex = generate_resume_action(
        uploaded_file=None,
        job_title="ML Intern",
        company="DeepMind",
        location="Remote",
        work_model="Remote",
        job_description="Build RAG with LlamaIndex and vector stores.",
        technologies="Python, LlamaIndex, ChromaDB",
        pipeline=mock_pipeline,
        chain=mock_chain,
        formatter=mock_formatter,
    )

    assert "Success!" in status
    assert pdf_path == str(fake_pdf)
    assert "DeepMind" in info_md
    assert "XYZ Formula" in guidelines
    assert "\\documentclass{article}" in rendered_tex


def test_generate_resume_action_chain_failure_handled(tmp_path: Path) -> None:
    """Test that an error inside the generation chain is handled gracefully without crashing."""
    from unittest.mock import MagicMock
    from src.app import generate_resume_action

    mock_pipeline = MagicMock()
    mock_pipeline.get_context_for_job.return_value = "Guidelines text"

    mock_chain = MagicMock()
    mock_chain.generate.side_effect = RuntimeError("API quota exceeded or network timeout")

    status, pdf_path, info_md, guidelines, rendered_tex = generate_resume_action(
        uploaded_file=None,
        job_title="Data Intern",
        company="Tech Co",
        location="",
        work_model="Hybrid",
        job_description="Sample description",
        technologies="",
        pipeline=mock_pipeline,
        chain=mock_chain,
    )

    assert "Generation Failed" in status
    assert "API quota exceeded" in status
    assert pdf_path is None
