"""Gradio web application for RAG Resume Generator."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import gradio as gr
from llama_index.core.schema import NodeWithScore

from src.config import ALLOWED_GENERATION_MODELS, get_settings
from src.data.candidate import CandidateProfile
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.generation.chain import (
    ResumeGenerationChain,
    get_gemini_llm,
)
from src.generation.formatter import ResumeFormatter
from src.generation.variants.v1_verified import V1Trace, generate_v1
from src.retrieval.pipeline import KnowledgeBasePipeline
from src.retrieval.retriever import format_retrieved_context

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Candidate Profile Helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# RAG Transparency & Generation Helpers
# ---------------------------------------------------------------------------

def format_rag_transparency_report(
    job: JobPosting,
    retrieved_nodes: list[NodeWithScore],
) -> str:
    """Generate an analytical transparency report for the RAG retrieval.

    Args:
        job: JobPosting instance queried.
        retrieved_nodes: Ranked list of retrieved nodes with RRF scores.

    Returns:
        str: Comprehensive Markdown report detailing search query, sources, and scores.
    """
    if not retrieved_nodes:
        return "*No relevant guidelines retrieved from the knowledge base for this query.*"

    table_rows = []
    for i, item in enumerate(retrieved_nodes, start=1):
        meta = item.node.metadata or {}
        topic = meta.get("topic", "Best Practice")
        category = meta.get("category", "General")
        file_name = meta.get("file_name", "doc.md")
        score_val = f"{item.score:.4f}" if item.score is not None else "N/A"
        table_rows.append(f"| {i} | **{topic}** | `{category}` | `{file_name}` | **{score_val}** |")

    table_md = "\n".join(table_rows)

    snippets = []
    for i, item in enumerate(retrieved_nodes, start=1):
        meta = item.node.metadata or {}
        topic = meta.get("topic", "Guideline")
        category = meta.get("category", "Category")
        score_val = f"(RRF Score: {item.score:.4f})" if item.score is not None else ""
        content = item.node.get_content().strip()
        snippets.append(
            f"#### 📌 Guideline {i}: {topic} `{category}` {score_val}\n\n{content}"
        )

    snippets_md = "\n\n---\n\n".join(snippets)

    return f"""### 🔍 RAG Retrieval Transparency & Source Breakdown
- **Target Query:** `{job.to_search_query()}`
- **Retrieved Chunks:** {len(retrieved_nodes)}
- **Reranker:** Reciprocal Rank Fusion (RRF, k=60) combining ChromaDB Vector Index + BM25 Sparse Search

| # | Topic | Category | Source Document | RRF Score |
|---|---|---|---|---|
{table_md}

---
### 📖 Verified Knowledge Base Content Injected into LLM Prompt:

{snippets_md}
"""


# ---------------------------------------------------------------------------
# History Management Helpers
# ---------------------------------------------------------------------------

def list_generated_resumes(output_dir: Path | str | None = None) -> list[dict[str, Any]]:
    """Scan output directory and list all generated PDF resumes with metadata.

    Args:
        output_dir: Output directory path. Defaults to settings value.

    Returns:
        list[dict[str, Any]]: List of dictionary metadata sorted by most recent first.
    """
    settings = get_settings()
    path = Path(output_dir) if output_dir else Path(settings.output_dir)

    if not path.exists():
        return []

    pdf_files = list(path.glob("*.pdf"))
    resumes = []

    for pdf in pdf_files:
        stat = pdf.stat()
        mod_time = datetime.fromtimestamp(stat.st_mtime)
        size_kb = stat.st_size / 1024
        tex_path = pdf.with_suffix(".tex")

        resumes.append({
            "filename": pdf.name,
            "path": str(pdf),
            "tex_path": str(tex_path) if tex_path.exists() else None,
            "mtime": stat.st_mtime,
            "generated_at": mod_time.strftime("%Y-%m-%d %H:%M:%S"),
            "size": f"{size_kb:.1f} KB",
            "has_tex": "Yes" if tex_path.exists() else "No",
        })

    # Sort descending by modification time (most recent first)
    resumes.sort(key=lambda r: r["mtime"], reverse=True)
    return resumes


def get_history_table_data(output_dir: Path | str | None = None) -> list[list[str]]:
    """Return table-friendly rows for Gradio Dataframe.

    Args:
        output_dir: Output directory path.

    Returns:
        list[list[str]]: List of row values.
    """
    resumes = list_generated_resumes(output_dir)
    return [
        [r["filename"], r["generated_at"], r["size"], r["has_tex"]]
        for r in resumes
    ]


def get_history_choices(output_dir: Path | str | None = None) -> list[str]:
    """Return filenames of available generated resumes for Dropdown.

    Args:
        output_dir: Output directory path.

    Returns:
        list[str]: Filenames of generated resumes.
    """
    resumes = list_generated_resumes(output_dir)
    return [r["filename"] for r in resumes]


def on_select_history_resume(
    filename: str,
    output_dir: Path | str | None = None,
) -> tuple[str | None, str | None, str]:
    """Load a historical resume's PDF and LaTeX source when selected from the dropdown.

    Args:
        filename: Selected resume filename.
        output_dir: Output directory path.

    Returns:
        tuple containing:
          - pdf_file_path (str | None)
          - tex_file_path (str | None)
          - tex_code_str (str)
    """
    if not filename:
        return None, None, ""

    settings = get_settings()
    path = Path(output_dir) if output_dir else Path(settings.output_dir)
    pdf_path = path / filename

    if not pdf_path.exists():
        return None, None, f"File `{filename}` not found."

    tex_path = pdf_path.with_suffix(".tex")
    tex_content = ""
    tex_file_ret = None
    if tex_path.exists():
        tex_file_ret = str(tex_path)
        try:
            tex_content = tex_path.read_text(encoding="utf-8")
        except Exception as e:
            tex_content = f"Could not read LaTeX source: {e}"

    return str(pdf_path), tex_file_ret, tex_content


# ---------------------------------------------------------------------------
# Main Action Workflow
# ---------------------------------------------------------------------------

def generate_resume_action(
    uploaded_file: Any,
    job_title: str,
    company: str,
    location: str,
    work_model: str,
    job_description: str,
    technologies: str,
    resume_language: str = "auto",
    gemini_model: str | None = None,
    temperature: float | None = None,
    top_k: int = 5,
    force_reindex: bool = False,
    pipeline: KnowledgeBasePipeline | None = None,
    chain: ResumeGenerationChain | None = None,
    formatter: ResumeFormatter | None = None,
) -> tuple[str, str | None, str | None, str, str, str, list[list[str]], gr.Dropdown]:
    """Execute the end-to-end resume generation workflow with full RAG transparency.

    Returns:
        tuple containing:
          - pipeline_status (Markdown status string)
          - pdf_path (Path to generated PDF for gr.File download, or None)
          - tex_path (Path to generated LaTeX source for gr.File download, or None)
          - pdf_info (Markdown metadata about the compiled PDF)
          - rag_guidelines (Markdown transparency report of retrieved guidelines)
          - rendered_tex (Raw LaTeX source code string)
          - updated_history_table (Refreshed table rows)
          - updated_history_dropdown (Refreshed dropdown with newly generated item)
    """
    start_time = time.time()
    current_choices = get_history_choices()

    # 1. Validation
    if not job_title or not job_title.strip():
        return (
            "⚠️ **Missing Field:** Please provide a Job Title.",
            None,
            None,
            "",
            "",
            "",
            get_history_table_data(),
            gr.Dropdown(choices=current_choices, value=current_choices[0] if current_choices else None),
        )
    if not company or not company.strip():
        return (
            "⚠️ **Missing Field:** Please provide a Hiring Company.",
            None,
            None,
            "",
            "",
            "",
            get_history_table_data(),
            gr.Dropdown(choices=current_choices, value=current_choices[0] if current_choices else None),
        )
    if not job_description or not job_description.strip():
        return (
            "⚠️ **Missing Field:** Please paste the Job Description / Requirements.",
            None,
            None,
            "",
            "",
            "",
            get_history_table_data(),
            gr.Dropdown(choices=current_choices, value=current_choices[0] if current_choices else None),
        )

    settings = get_settings()

    # 2. Resolve Candidate Profile
    try:
        if uploaded_file is not None:
            if isinstance(uploaded_file, (str, Path)):
                profile_path = Path(uploaded_file)
            elif hasattr(uploaded_file, "name"):
                profile_path = Path(uploaded_file.name)
            elif isinstance(uploaded_file, dict) and "path" in uploaded_file:
                profile_path = Path(uploaded_file["path"])
            else:
                profile_path = Path(str(uploaded_file))
        else:
            profile_path = Path(settings.candidate_profile_path)

        candidate, _ = load_candidate_profile_from_path(profile_path)
    except Exception as e:
        logger.error("Failed to load candidate profile: %s", e)
        return (
            f"❌ **Profile Error:** {e}",
            None,
            None,
            "",
            "",
            "",
            get_history_table_data(),
            gr.Dropdown(choices=current_choices, value=current_choices[0] if current_choices else None),
        )

    # 3. Build JobPosting instance
    tech_list = [t.strip() for t in technologies.split(",") if t.strip()]
    job = JobPosting(
        title=job_title.strip(),
        company=company.strip(),
        location=location.strip() or "Not specified",
        work_model=work_model,
        raw_description=job_description.strip(),
        technologies=tech_list,
        keywords=tech_list[:5],
    )

    try:
        # 4. RAG Retrieval: Extract guidelines & generate transparency report
        logger.info("Executing RAG retrieval for job: %s @ %s", job.title, job.company)
        active_pipeline = pipeline if pipeline is not None else KnowledgeBasePipeline(
            similarity_top_k=int(top_k),
            bm25_top_k=int(top_k),
        )
        if force_reindex:
            active_pipeline.setup(force_reindex=True)

        retrieved_nodes = active_pipeline.retrieve_for_job(job=job, top_k=int(top_k))
        guidelines_context = format_retrieved_context(retrieved_nodes)
        transparency_report = format_rag_transparency_report(job=job, retrieved_nodes=retrieved_nodes)

        # 5. LLM Generation: Structured TailoredResume via Verified V1 Loop
        selected_model = gemini_model or settings.generation_model
        selected_temp = temperature if temperature is not None else settings.generation_temperature
        trace: V1Trace | None = None

        if chain is not None:
            # Direct chain injection (e.g. mock test suite)
            logger.info("Invoking injected generation chain (lang=%s)...", resume_language)
            tailored_resume = chain.generate(
                candidate=candidate,
                job=job,
                retrieved_guidelines=guidelines_context,
                language=resume_language,
            )
        else:
            # Production default: full V1 verifier loop (error-guided regeneration + deterministic repair)
            logger.info(
                "Invoking V1 Verified Generator (model=%s, temp=%.2f, lang=%s)...",
                selected_model,
                selected_temp,
                resume_language,
            )
            active_chain = ResumeGenerationChain(
                llm=get_gemini_llm(model_name=selected_model, temperature=selected_temp)
            )
            active_judge = None
            try:
                from src.evaluation.claim_judge import ClaimLevelJudge
                active_judge = ClaimLevelJudge()
            except Exception as e:
                logger.warning("Could not initialize ClaimLevelJudge for production generation: %s", e)

            tailored_resume, trace = generate_v1(
                candidate=candidate,
                job=job,
                pipeline=active_pipeline,
                chain=active_chain,
                judge=active_judge,
                top_k=int(top_k),
                language=resume_language,
            )

        # 6. Formatting & LaTeX PDF Compilation
        logger.info("Rendering LaTeX and compiling with Tectonic...")
        active_formatter = formatter if formatter is not None else ResumeFormatter()
        rendered_tex = active_formatter.render_latex(tailored_resume, contact=candidate.contact)
        pdf_path = active_formatter.compile_pdf(tailored_resume, keep_tex=True, contact=candidate.contact)
        tex_path = pdf_path.with_suffix(".tex")

        elapsed = time.time() - start_time
        pdf_size_kb = pdf_path.stat().st_size / 1024

        lang_names = {"pt": "Português", "en": "Inglês", "fr": "Francês"}
        active_lang_name = lang_names.get(tailored_resume.language, tailored_resume.language.upper())

        if trace is not None:
            path_labels = {
                "clean@0": "🛡️ Verified Clean (Round 0 — 0 defects)",
                "clean@1": "🛡️ Verified Clean (Retry 1 — corrected via feedback)",
                "clean@2": "🛡️ Verified Clean (Retry 2 — corrected via feedback)",
                "repaired": "🔧 Deterministically Repaired (residual defects purged)",
                "fallback": "📦 Deterministic Fallback Floor (B0)",
            }
            res_label = path_labels.get(trace.final_path, trace.final_path)
            status_msg = f"🟢 **Success!** Tailored resume generated in **{active_lang_name}** | **{res_label}** | Compiled in **{elapsed:.1f}s**."
            verification_line = f"- **Verification Path:** `{trace.final_path}` ({trace.total_rounds} rounds, {trace.repair_actions_count} repair actions)\n"
            transparency_report += (
                f"\n\n---\n### 🛡️ Verification & Faithfulness Summary\n"
                f"- **Resolution Path:** `{trace.final_path}`\n"
                f"- **Rounds Completed:** {trace.total_rounds}\n"
                f"- **Repair Surgery Actions:** {trace.repair_actions_count}\n"
            )
        else:
            status_msg = f"🟢 **Success!** Tailored resume generated in **{active_lang_name}** and compiled in **{elapsed:.1f}s**."
            verification_line = ""

        pdf_info_md = f"""### 📄 Resume Compiled Successfully!
- **File:** `{pdf_path.name}`
- **Size:** `{pdf_size_kb:.1f} KB`
- **Candidate:** **{tailored_resume.header.full_name}**
- **Target Role:** **{tailored_resume.target_job_title}** @ **{tailored_resume.target_company}**
- **Language:** **{active_lang_name} ({tailored_resume.language.upper()})**
{verification_line}- **Format:** Strict 1-Page PDF (ATS & Recruiter Optimized)
- **Compiler:** Tectonic Standalone TeX Engine
"""
        new_history = get_history_table_data(output_dir=pdf_path.parent)
        new_choices = get_history_choices(output_dir=pdf_path.parent)
        if pdf_path.name not in new_choices:
            new_choices.insert(0, pdf_path.name)

        return (
            status_msg,
            str(pdf_path),
            str(tex_path),
            pdf_info_md,
            transparency_report,
            rendered_tex,
            new_history,
            gr.Dropdown(choices=new_choices, value=pdf_path.name),
        )

    except Exception as e:
        logger.error("End-to-end generation failed: %s", e, exc_info=True)
        return (
            f"❌ **Generation Failed:** {e}",
            None,
            None,
            f"⚠️ **Error details:**\n```\n{e}\n```",
            "",
            "",
            get_history_table_data(),
            gr.Dropdown(choices=current_choices, value=current_choices[0] if current_choices else None),
        )


def build_app() -> gr.Blocks:
    """Build the complete Gradio application layout and connect workflow actions.

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
                        placeholder="e.g. São Paulo, SP or Brest, France",
                        value="São Paulo, SP",
                    )
                    work_model_input = gr.Dropdown(
                        choices=["Hybrid", "Remote", "On-site"],
                        value="Hybrid",
                        label="Work Model",
                    )
                    language_dropdown = gr.Dropdown(
                        choices=[
                            ("Automático (detectar da vaga)", "auto"),
                            ("Português (PT-BR)", "pt"),
                            ("Inglês (EN)", "en"),
                            ("Francês (FR)", "fr"),
                        ],
                        value="auto",
                        label="Idioma do Currículo / Language",
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
                        choices=ALLOWED_GENERATION_MODELS,
                        value=settings.generation_model,
                        allow_custom_value=True,
                        label="Gemini LLM Model",
                    )
                    temp_slider = gr.Slider(
                        minimum=0.0,
                        maximum=1.0,
                        value=settings.generation_temperature,
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
                        tex_download = gr.File(
                            label="Download LaTeX Source (.tex)",
                            interactive=False,
                        )
                        tex_code_display = gr.Code(
                            language="latex",
                            label="Rendered LaTeX Source Code",
                            interactive=False,
                        )

                    with gr.Tab("📁 Generation History"):
                        with gr.Row():
                            history_refresh_btn = gr.Button("🔄 Refresh History", size="sm")

                        initial_history_rows = get_history_table_data()
                        initial_choices = get_history_choices()

                        history_table = gr.Dataframe(
                            headers=["Filename", "Generated At", "Size", "Has .tex"],
                            value=initial_history_rows,
                            label="Previously Generated Resumes in output/",
                            interactive=False,
                        )

                        history_selector = gr.Dropdown(
                            choices=initial_choices,
                            value=initial_choices[0] if initial_choices else None,
                            label="Select Past Resume to Inspect & Download",
                        )

                        with gr.Row():
                            history_pdf_download = gr.File(label="Download Historical PDF", interactive=False)
                            history_tex_download = gr.File(label="Download Historical .tex", interactive=False)

                        history_tex_code = gr.Code(
                            language="latex",
                            label="Historical LaTeX Source Code",
                            interactive=False,
                        )

        # -----------------------------------------------------------------
        # Event Handlers
        # -----------------------------------------------------------------

        # 1. Main generation button
        generate_btn.click(
            fn=generate_resume_action,
            inputs=[
                profile_upload,
                job_title_input,
                company_input,
                location_input,
                work_model_input,
                job_desc_input,
                tech_input,
                language_dropdown,
                model_dropdown,
                temp_slider,
                top_k_slider,
                force_reindex,
            ],
            outputs=[
                pipeline_status,
                pdf_download,
                tex_download,
                pdf_info_display,
                rag_guidelines_display,
                tex_code_display,
                history_table,
                history_selector,
            ],
        )

        # 2. History selector change
        history_selector.change(
            fn=on_select_history_resume,
            inputs=[history_selector],
            outputs=[
                history_pdf_download,
                history_tex_download,
                history_tex_code,
            ],
        )

        # 3. Refresh history button
        def refresh_history_action() -> tuple[list[list[str]], gr.Dropdown]:
            choices = get_history_choices()
            return get_history_table_data(), gr.Dropdown(choices=choices, value=choices[0] if choices else None)

        history_refresh_btn.click(
            fn=refresh_history_action,
            inputs=[],
            outputs=[history_table, history_selector],
        )

    return app


# Application singleton
app = build_app()

if __name__ == "__main__":
    app.launch()
