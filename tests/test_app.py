"""Unit tests for the Gradio web application layout and handlers in src/app.py."""

from __future__ import annotations

from pathlib import Path
import time
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
    status, pdf, tex, info, guide, raw_tex, table, dropdown = generate_resume_action(
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
    assert tex is None

    # Missing company
    status, pdf, tex, info, guide, raw_tex, table, dropdown = generate_resume_action(
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
    status, pdf, tex, info, guide, raw_tex, table, dropdown = generate_resume_action(
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
    from llama_index.core.schema import NodeWithScore, TextNode
    from src.app import generate_resume_action
    from src.data.resume import ResumeHeader, TailoredResume

    # Mock pipeline returning structured NodeWithScore
    mock_node = TextNode(
        text="Quantify your engineering achievements using the XYZ formula.",
        metadata={"category": "resume_best_practices", "topic": "XYZ Formula", "file_name": "02_xyz.md"},
        id_="node_1",
    )
    mock_pipeline = MagicMock()
    mock_pipeline.retrieve_for_job.return_value = [NodeWithScore(node=mock_node, score=0.0325)]

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

    # Mock formatter & fake compiled PDF + TeX
    fake_pdf = tmp_path / "test_resume.pdf"
    fake_pdf.write_bytes(b"%PDF-1.5 fake pdf content for test")
    fake_tex = tmp_path / "test_resume.tex"
    fake_tex.write_text("\\documentclass{article}", encoding="utf-8")

    mock_formatter = MagicMock()
    mock_formatter.render_latex.return_value = "\\documentclass{article}\\begin{document}Hello\\end{document}"
    mock_formatter.compile_pdf.return_value = fake_pdf

    status, pdf_path, tex_path, info_md, guidelines, rendered_tex, table, dropdown = generate_resume_action(
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
    assert tex_path == str(fake_tex)
    assert "DeepMind" in info_md
    assert "XYZ Formula" in guidelines
    assert "0.0325" in guidelines
    assert "\\documentclass{article}" in rendered_tex


def test_generate_resume_action_chain_failure_handled(tmp_path: Path) -> None:
    """Test that an error inside the generation chain is handled gracefully without crashing."""
    from unittest.mock import MagicMock
    from src.app import generate_resume_action

    mock_pipeline = MagicMock()
    mock_pipeline.retrieve_for_job.return_value = []

    mock_chain = MagicMock()
    mock_chain.generate.side_effect = RuntimeError("API quota exceeded or network timeout")

    status, pdf_path, tex_path, info_md, guidelines, rendered_tex, table, dropdown = generate_resume_action(
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
    assert tex_path is None


def test_format_rag_transparency_report() -> None:
    """Test formatting the analytical RAG transparency report."""
    from llama_index.core.schema import NodeWithScore, TextNode
    from src.app import format_rag_transparency_report
    from src.data.job_posting import JobPosting

    job = JobPosting(
        title="AI Engineer",
        company="Tech Corp",
        raw_description="Looking for AI engineer.",
        technologies=["Python", "FastAPI"],
    )

    # Empty test
    empty_report = format_rag_transparency_report(job, [])
    assert "No relevant guidelines" in empty_report

    # Populated test
    node = TextNode(
        text="ATS systems look for linear headings.",
        metadata={"category": "resume_best_practices", "topic": "ATS Formatting", "file_name": "04_ats.md"},
    )
    scored = [NodeWithScore(node=node, score=0.025)]

    report = format_rag_transparency_report(job, scored)
    assert "ATS Formatting" in report
    assert "04_ats.md" in report
    assert "0.0250" in report
    assert "Reciprocal Rank Fusion" in report


# ---------------------------------------------------------------------------
# History tests (Task 4.4)
# ---------------------------------------------------------------------------

def test_list_generated_resumes_empty(tmp_path: Path) -> None:
    """Test list_generated_resumes on empty or missing folder."""
    from src.app import list_generated_resumes

    empty_dir = tmp_path / "empty_out"
    empty_dir.mkdir()
    assert list_generated_resumes(empty_dir) == []

    missing_dir = tmp_path / "missing_dir"
    assert list_generated_resumes(missing_dir) == []


def test_list_generated_resumes_populated(tmp_path: Path) -> None:
    """Test list_generated_resumes returns metadata sorted by mtime descending."""
    from src.app import get_history_choices, get_history_table_data, list_generated_resumes

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    pdf1 = out_dir / "resume_older.pdf"
    pdf1.write_bytes(b"%PDF-older")
    time.sleep(0.05)

    pdf2 = out_dir / "resume_newer.pdf"
    pdf2.write_bytes(b"%PDF-newer")
    tex2 = out_dir / "resume_newer.tex"
    tex2.write_text("\\documentclass{article}", encoding="utf-8")

    resumes = list_generated_resumes(out_dir)
    assert len(resumes) == 2
    # Most recent should be first
    assert resumes[0]["filename"] == "resume_newer.pdf"
    assert resumes[0]["has_tex"] == "Yes"
    assert resumes[1]["filename"] == "resume_older.pdf"
    assert resumes[1]["has_tex"] == "No"

    table_data = get_history_table_data(out_dir)
    assert len(table_data) == 2
    assert table_data[0][0] == "resume_newer.pdf"

    choices = get_history_choices(out_dir)
    assert choices == ["resume_newer.pdf", "resume_older.pdf"]


def test_on_select_history_resume(tmp_path: Path) -> None:
    """Test selecting a historical resume loads PDF path and LaTeX content."""
    from src.app import on_select_history_resume

    out_dir = tmp_path / "out"
    out_dir.mkdir()

    pdf = out_dir / "resume_test.pdf"
    pdf.write_bytes(b"%PDF-test")
    tex = out_dir / "resume_test.tex"
    tex.write_text("\\documentclass{article}\\begin{document}Test\\end{document}", encoding="utf-8")

    # Valid selection
    pdf_ret, tex_ret, code = on_select_history_resume("resume_test.pdf", output_dir=out_dir)
    assert pdf_ret == str(pdf)
    assert tex_ret == str(tex)
    assert "\\documentclass{article}" in code

    # Non-existent selection
    pdf_none, tex_none, err = on_select_history_resume("does_not_exist.pdf", output_dir=out_dir)
    assert pdf_none is None
    assert "not found" in err

    # Empty selection
    pdf_empty, tex_empty, blank = on_select_history_resume("", output_dir=out_dir)
    assert pdf_empty is None
