"""Unit tests for knowledge base ingestion and document loader."""

from pathlib import Path
import pytest

from src.ingestion.loader import KnowledgeBaseLoader, extract_title_from_markdown


def test_extract_title_from_markdown() -> None:
    """Test extracting H1 titles from various markdown strings."""
    # Standard H1 header
    md1 = "# Título Principal\nTexto explicativo aqui."
    assert extract_title_from_markdown(md1) == "Título Principal"

    # Header with leading/trailing spaces
    md2 = "\n\n  #   Outro Título  \nMais conteúdo."
    assert extract_title_from_markdown(md2) == "Outro Título"

    # No H1 header, should return default fallback
    md3 = "## Apenas H2\nTexto sem H1."
    assert extract_title_from_markdown(md3, default="Fallback") == "Fallback"

    # Empty string
    assert extract_title_from_markdown("", default="Vazio") == "Vazio"


def test_loader_load_category() -> None:
    """Test loading documents from a specific category directory."""
    loader = KnowledgeBaseLoader()
    docs = loader.load_category("resume_best_practices")

    assert len(docs) >= 5
    for doc in docs:
        assert doc.metadata["category"] == "resume_best_practices"
        assert len(doc.metadata["topic"]) > 0
        assert doc.metadata["file_name"].endswith(".md")
        assert len(doc.text) > 100


def test_loader_load_hr_recruitment_category() -> None:
    """Test loading documents from the hr_recruitment category."""
    loader = KnowledgeBaseLoader()
    docs = loader.load_category("hr_recruitment")

    assert len(docs) >= 5
    for doc in docs:
        assert doc.metadata["category"] == "hr_recruitment"
        assert len(doc.metadata["topic"]) > 0
        assert doc.metadata["file_name"].endswith(".md")


def test_loader_load_all_documents() -> None:
    """Test loading aggregated documents across all categories."""
    loader = KnowledgeBaseLoader()
    all_docs = loader.load_all_documents()

    # We created 5 in resume_best_practices + 5 in hr_recruitment = 10 documents
    assert len(all_docs) >= 10

    categories = {doc.metadata["category"] for doc in all_docs}
    assert "resume_best_practices" in categories
    assert "hr_recruitment" in categories


def test_loader_non_existent_category() -> None:
    """Test error handling when requesting an invalid category."""
    loader = KnowledgeBaseLoader()
    with pytest.raises(FileNotFoundError):
        loader.load_category("categoria_que_nao_existe")


def test_loader_custom_directory(tmp_path: Path) -> None:
    """Test loader with a custom/mock directory structure."""
    custom_category = tmp_path / "custom_kb"
    custom_category.mkdir(parents=True)
    sample_file = custom_category / "teste.md"
    sample_file.write_text("# Teste Customizado\nConteúdo para teste.", encoding="utf-8")

    loader = KnowledgeBaseLoader(knowledge_base_dir=tmp_path)
    docs = loader.load_category("custom_kb")

    assert len(docs) == 1
    assert docs[0].metadata["category"] == "custom_kb"
    assert docs[0].metadata["topic"] == "Teste Customizado"
    assert "Conteúdo para teste." in docs[0].text
