"""LaTeX template rendering and PDF compilation via Tectonic."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
import re
import shutil
import subprocess
from typing import Any

import jinja2

from src.config import get_settings
from src.data.candidate import ContactInfo
from src.data.resume import ResumeHeader, TailoredResume, _deep_escape

logger = logging.getLogger(__name__)


def build_jinja_environment(templates_dir: Path | str | None = None) -> jinja2.Environment:
    """Create a Jinja2 Environment with LaTeX-safe non-conflicting delimiters.

    Uses:
      - '<%' and '%>' for blocks
      - '<<' and '>>' for variables
      - '<#' and '#>' for comments

    Args:
        templates_dir: Directory containing templates. Defaults to settings.

    Returns:
        jinja2.Environment: Configured Jinja environment.
    """
    settings = get_settings()
    path = Path(templates_dir) if templates_dir else Path(settings.templates_dir)

    loader = jinja2.FileSystemLoader(str(path))
    return jinja2.Environment(
        loader=loader,
        block_start_string="<%",
        block_end_string="%>",
        variable_start_string="<<",
        variable_end_string=">>",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )


def sanitize_filename_part(text: str, fallback: str = "item") -> str:
    """Sanitize a string for safe usage in output filenames.

    Args:
        text: Raw company or candidate name.
        fallback: Default fallback if text contains no valid filename characters.

    Returns:
        str: Lowercase alphanumeric string with underscores.
    """
    slug = re.sub(r"[^\w\s-]", "", text.strip().lower())
    clean = re.sub(r"[-\s]+", "_", slug)[:30].strip("_")
    return clean if clean else fallback


class ResumeFormatter:
    """Renders LaTeX templates and compiles them into final PDF resumes.

    Attributes:
        templates_dir: Directory holding LaTeX .tex.j2 templates.
        output_dir: Directory where generated PDFs are placed.
        template_name: Name of the template file (default 'resume.tex.j2').
    """

    def __init__(
        self,
        templates_dir: Path | str | None = None,
        output_dir: Path | str | None = None,
        template_name: str = "resume.tex.j2",
    ) -> None:
        """Initialize ResumeFormatter with template and output paths.

        Args:
            templates_dir: Directory containing templates. Defaults to settings.
            output_dir: Directory for generated files. Defaults to settings.
            template_name: LaTeX Jinja2 template filename.
        """
        settings = get_settings()
        self.templates_dir = Path(templates_dir) if templates_dir else Path(settings.templates_dir)
        self.output_dir = Path(output_dir) if output_dir else Path(settings.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.template_name = template_name

        self.env = build_jinja_environment(self.templates_dir)

    def render_latex(
        self,
        resume: TailoredResume,
        contact: ContactInfo | None = None,
    ) -> str:
        """Render the LaTeX template into raw .tex string using escaped resume context.

        Args:
            resume: TailoredResume instance.
            contact: Optional verified ContactInfo to inject deterministically at render time.

        Returns:
            str: Rendered, LaTeX-escaped document string.
        """
        template = self.env.get_template(self.template_name)
        context = resume.to_latex_context()
        if contact is not None:
            header = ResumeHeader(
                full_name=contact.full_name,
                email=contact.email,
                phone=contact.phone,
                location=contact.location,
                linkedin_url=contact.linkedin_url,
                github_url=contact.github_url,
                portfolio_url=contact.portfolio_url,
            )
            context["header"] = _deep_escape(header.model_dump())
        return template.render(**context)

    def compile_pdf(
        self,
        resume: TailoredResume,
        output_filename: str | None = None,
        keep_tex: bool = True,
        contact: ContactInfo | None = None,
    ) -> Path:
        """Render and compile a TailoredResume into a PDF file.

        Args:
            resume: TailoredResume instance to format.
            output_filename: Optional custom PDF filename. Defaults to
                'resume_{company}_{date}.pdf'.
            keep_tex: Whether to keep the intermediate .tex source file.
            contact: Optional verified ContactInfo to inject deterministically at render time.

        Returns:
            Path: Path to the generated PDF file.

        Raises:
            RuntimeError: If Tectonic is not found or compilation fails.
        """
        # Determine output filename stem
        if output_filename:
            stem = Path(output_filename).stem
        else:
            company_slug = sanitize_filename_part(resume.target_company, fallback="company")
            date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            stem = f"resume_{company_slug}_{date_str}"

        tex_filename = f"{stem}.tex"
        pdf_filename = f"{stem}.pdf"

        tex_path = self.output_dir / tex_filename
        pdf_path = self.output_dir / pdf_filename

        # 1. Render and write .tex file
        rendered_tex = self.render_latex(resume, contact=contact)
        tex_path.write_text(rendered_tex, encoding="utf-8")
        logger.info("Wrote LaTeX source to %s", tex_path)

        # 2. Resolve Tectonic binary
        tectonic_bin = (
            shutil.which("tectonic")
            or "/home/samuel/.local/bin/tectonic"
        )
        if not Path(tectonic_bin).exists() and not shutil.which("tectonic"):
            raise RuntimeError(
                f"Tectonic LaTeX compiler not found at {tectonic_bin}. "
                "Please verify Tectonic installation."
            )

        # 3. Execute Tectonic compilation
        logger.info("Compiling PDF with Tectonic: %s -> %s", tex_path.name, pdf_path.name)
        cmd = [
            str(tectonic_bin),
            "-o",
            str(self.output_dir),
            str(tex_path),
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            error_msg = (
                f"Tectonic compilation failed with exit code {result.returncode}.\n"
                f"Stderr:\n{result.stderr}\nStdout:\n{result.stdout}"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

        if not pdf_path.exists():
            raise RuntimeError(f"Tectonic finished but PDF was not created at: {pdf_path}")

        logger.info("Successfully generated PDF resume at: %s", pdf_path)

        # 4. Cleanup intermediate .tex if requested
        if not keep_tex and tex_path.exists():
            tex_path.unlink()

        return pdf_path
