"""Gradio web application for RAG Resume Generator."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import gradio as gr
import yaml

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_candidate_profile_from_path(file_path: Path | str) -> tuple[CandidateProfile, str]:
    """Load and format a CandidateProfile from a YAML file.

    Args:
        file_path: Path to the candidate YAML file.

    Returns:
        tuple[CandidateProfile, str]: Parsed profile and formatted Markdown summary.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Candidate profile YAML not found at: {path}")

    profile = CandidateProfile.from_yaml(path)

    # Format quick summary for display in the UI
    edu_summary = ", ".join(f"{e.degree} ({e.institution})" for e in profile.education[:2])
    exp_summary = ", ".join(f"{x.title} @ {x.organization}" for x in profile.experiences[:2])
    skills_top = ", ".join(profile.skills.programming_languages[:4])

    summary_md = f"""### 👤 Active Candidate Profile: **{profile.contact.full_name}**
- **Contact:** `{profile.contact.email}` | `{profile.contact.location}`
- **Education:** {edu_summary or "None listed"}
- **Recent Experience:** {exp_summary or "None listed"}
- **Core Languages:** {skills_top or "None listed"}
- **Source File:** `{path.name}`
"""
    return profile, summary_md


def handle_profile_upload(file: Any) -> tuple[str, str]:
    """Handle custom candidate profile YAML upload.

    Args:
        file: Gradio file wrapper object or file path.

    Returns:
        tuple[str, str]: Status message and updated candidate summary Markdown.
    """
    if file is None:
        default_path = Path(get_settings().candidate_profile_path)
        try:
            _, summary_md = load_candidate_profile_from_path(default_path)
            return "Reverted to default candidate profile.", summary_md
        except Exception as e:
            return f"Error loading default profile: {e}", "No active profile."

    if isinstance(file, (str, Path)):
        file_path = Path(file)
    elif hasattr(file, "name"):
        file_path = Path(file.name)
    elif isinstance(file, dict) and "path" in file:
        file_path = Path(file["path"])
    else:
        file_path = Path(str(file))

    try:
        _, summary_md = load_candidate_profile_from_path(file_path)
        return f"Successfully loaded custom profile from `{file_path.name}`.", summary_md
    except Exception as e:
        logger.error("Failed to load uploaded candidate profile: %s", e)
        return f"❌ Invalid candidate YAML profile: {e}", "Error in uploaded file. Please check schema."


def build_app() -> gr.Blocks:
    """Build the complete Gradio application layout and input/output panels.

    Returns:
        gr.Blocks: Configured Gradio interface.
    """
    settings = get_settings()
    default_profile_path = Path(settings.candidate_profile_path)

    # Preload default profile summary
    try:
        _, initial_summary_md = load_candidate_profile_from_path(default_profile_path)
    except Exception as e:
        initial_summary_md = f"⚠️ Could not preload `{default_profile_path}`: {e}"

    custom_theme = gr.themes.Soft(
        primary_hue="blue",
        secondary_hue="slate",
    )

    with gr.Blocks(title="RAG Resume Tailor") as app:
        # Header banner
        gr.Markdown(
            """# 🎓 RAG Resume Tailor — Internship Edition
AI-powered, ATS-optimized, 1-page resume generator combining your verified background with recruitment best practices.
            """
        )

        with gr.Row():
            # -----------------------------------------------------------------
            # LEFT COLUMN: Inputs & Configuration
            # -----------------------------------------------------------------
            with gr.Column(scale=5):
                gr.Markdown("### 1️⃣ Candidate Profile")
                candidate_summary_box = gr.Markdown(value=initial_summary_md)

                profile_upload = gr.File(
                    label="Upload Custom Profile YAML (Optional)",
                    file_types=[".yaml", ".yml"],
                    file_count="single",
                )
                profile_status = gr.Markdown(value="*Using default candidate profile.*")

                profile_upload.change(
                    fn=handle_profile_upload,
                    inputs=[profile_upload],
                    outputs=[profile_status, candidate_summary_box],
                )

                gr.Markdown("---")
                gr.Markdown("### 2️⃣ Target Internship Details")

                job_title_input = gr.Textbox(
                    label="Job Title *",
                    placeholder="e.g. Machine Learning Engineering Intern",
                    value="Machine Learning Engineering Intern",
                )
                company_input = gr.Textbox(
                    label="Hiring Company *",
                    placeholder="e.g. Google DeepMind, Nubank, Itaú, Startup AI",
                    value="DeepMind Technologies",
                )

                with gr.Row():
                    location_input = gr.Textbox(
                        label="Location",
                        placeholder="e.g. São Paulo, SP",
                        value="São Paulo, SP",
                    )
                    work_model_input = gr.Dropdown(
                        choices=["Hybrid", "Remote", "On-site"],
                        value="Hybrid",
                        label="Work Model",
                    )

                job_desc_input = gr.Textbox(
                    label="Job Description & Responsibilities *",
                    placeholder="Paste the full job posting description here...",
                    lines=6,
                    value=(
                        "We are seeking an enthusiastic Machine Learning Engineering Intern to join our team.\n"
                        "Key responsibilities:\n"
                        "- Build and experiment with Retrieval-Augmented Generation (RAG) pipelines.\n"
                        "- Implement vector search using ChromaDB and LLM orchestration with LlamaIndex.\n"
                        "- Write clean, tested Python code (pytest) and integrate RESTful APIs.\n"
                        "- Collaborate in an agile Scrum environment."
                    ),
                )

                tech_input = gr.Textbox(
                    label="Tech Stack & Keywords (comma-separated)",
                    placeholder="e.g. Python, LlamaIndex, ChromaDB, FastAPI, Docker",
                    value="Python, LlamaIndex, ChromaDB, FastAPI, Docker, PyTorch",
                )

                with gr.Accordion("⚙️ Advanced RAG & LLM Settings", open=False):
                    model_dropdown = gr.Dropdown(
                        choices=["gemini-2.5-flash", "gemini-2.5-pro"],
                        value=settings.gemini_model,
                        label="Gemini LLM Model",
                    )
                    temp_slider = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=settings.gemini_temperature,
                        step=0.05,
                        label="LLM Temperature (Low = Deterministic)",
                    )
                    top_k_slider = gr.Slider(
                        minimum=1,
                        maximum=10,
                        value=5,
                        step=1,
                        label="RAG Knowledge Guidelines (Top-K)",
                    )
                    force_reindex = gr.Checkbox(
                        label="Force Re-index Knowledge Base in ChromaDB",
                        value=False,
                    )

                generate_btn = gr.Button(
                    "⚡ Generate Tailored Resume",
                    variant="primary",
                    size="lg",
                )

            # -----------------------------------------------------------------
            # RIGHT COLUMN: Outputs & Previews
            # -----------------------------------------------------------------
            with gr.Column(scale=6):
                gr.Markdown("### 3️⃣ Generated Resume & Verification")
                pipeline_status = gr.Markdown("🟢 **Status:** Ready. Click *Generate Tailored Resume* to start.")

                with gr.Tabs():
                    with gr.Tab("📄 PDF Preview & Download"):
                        pdf_download = gr.File(
                            label="Download Compiled PDF",
                            interactive=False,
                        )
                        pdf_info_display = gr.Markdown(
                            "*PDF will appear here ready for preview and download once generated.*"
                        )

                    with gr.Tab("🧠 RAG Guidelines Applied"):
                        rag_guidelines_display = gr.Markdown(
                            "*Recruitment advice and ATS best practices retrieved specifically for this job will be shown here.*"
                        )

                    with gr.Tab("💻 LaTeX Source (.tex)"):
                        tex_code_display = gr.Code(
                            language="latex",
                            label="Rendered LaTeX Source Code",
                            interactive=False,
                        )

    return app


# Application singleton
app = build_app()

if __name__ == "__main__":
    app.launch()
