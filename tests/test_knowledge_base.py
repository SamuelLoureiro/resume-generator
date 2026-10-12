"""Unit tests verifying knowledge base files in src/knowledge_base/."""

from pathlib import Path


# Expected filenames for each knowledge base category
EXPECTED_RESUME_BEST_PRACTICES = {
    "01_resume_structure_for_internships.md",
    "02_star_xyz_bullet_writing.md",
    "03_action_verbs_and_vocabulary.md",
    "04_ats_optimization.md",
    "05_common_mistakes_and_red_flags.md",
}

EXPECTED_HR_RECRUITMENT = {
    "01_what_recruiters_look_for_in_interns.md",
    "02_big_techs_vs_startups.md",
    "03_soft_skills_and_competitive_differentiators.md",
    "04_valuing_academic_experience_and_projects.md",
    "05_adaptation_by_technical_track.md",
    "06_data_engineering_internships.md",
    "07_systems_and_core_swe_internships.md",
    "08_embedded_systems_and_edge_ai.md",
}


def test_knowledge_base_documents_exist() -> None:
    """Verify that knowledge base directories contain the expected English markdown files."""
    kb_root = Path("src/knowledge_base")
    assert kb_root.exists(), "src/knowledge_base directory must exist"

    best_practices_dir = kb_root / "resume_best_practices"
    hr_recruitment_dir = kb_root / "hr_recruitment"

    assert best_practices_dir.exists(), "resume_best_practices directory must exist"
    assert hr_recruitment_dir.exists(), "hr_recruitment directory must exist"

    bp_files = list(best_practices_dir.glob("*.md"))
    hr_files = list(hr_recruitment_dir.glob("*.md"))

    assert len(bp_files) >= 5, f"Expected at least 5 best practices docs, found {len(bp_files)}"
    assert len(hr_files) >= 5, f"Expected at least 5 HR recruitment docs, found {len(hr_files)}"

    # Ensure every markdown file has substantial content and UTF-8 encoding
    for doc in bp_files + hr_files:
        content = doc.read_text(encoding="utf-8")
        assert len(content.strip()) > 500, f"File {doc.name} has insufficient content"
        assert "# " in content, f"File {doc.name} missing markdown headers"


def test_knowledge_base_filenames_are_english() -> None:
    """Verify that all knowledge base filenames follow the English naming convention."""
    kb_root = Path("src/knowledge_base")

    bp_filenames = {f.name for f in (kb_root / "resume_best_practices").glob("*.md")}
    hr_filenames = {f.name for f in (kb_root / "hr_recruitment").glob("*.md")}

    assert bp_filenames == EXPECTED_RESUME_BEST_PRACTICES, (
        f"Unexpected resume_best_practices files.\n"
        f"Expected: {EXPECTED_RESUME_BEST_PRACTICES}\n"
        f"Found:    {bp_filenames}"
    )

    assert hr_filenames == EXPECTED_HR_RECRUITMENT, (
        f"Unexpected hr_recruitment files.\n"
        f"Expected: {EXPECTED_HR_RECRUITMENT}\n"
        f"Found:    {hr_filenames}"
    )


def test_knowledge_base_h1_titles_are_present() -> None:
    """Verify that every knowledge base document has a valid H1 title."""
    kb_root = Path("src/knowledge_base")

    all_docs = list(kb_root.glob("**/*.md"))
    assert len(all_docs) >= 10, f"Expected at least 10 KB documents, found {len(all_docs)}"

    for doc in all_docs:
        content = doc.read_text(encoding="utf-8")
        lines = content.splitlines()
        h1_lines = [line for line in lines if line.startswith("# ")]
        assert len(h1_lines) >= 1, f"File {doc.name} is missing an H1 title (# ...)."
