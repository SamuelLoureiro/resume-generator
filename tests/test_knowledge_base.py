"""Unit tests verifying knowledge base files in src/knowledge_base/."""

from pathlib import Path


def test_knowledge_base_documents_exist() -> None:
    """Verify that knowledge base directories contain markdown files."""
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
