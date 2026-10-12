"""Golden regression tests for the Amazon SDE Intern resume.

These tests ensure that known defects identified in docs/audit_report.md
(fabrication, verb inflation, leadership omission, broken URLs, phone formatting,
and empty certification titles) are consistently caught and that a verified,
corrected resume passes all checks.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import pytest

from tests.golden.checks import (
    check_contact_links_have_https_scheme,
    check_leadership_and_team_size_preserved,
    check_no_bare_profile_as_project_url,
    check_no_empty_certifications_in_section_title,
    check_no_fabricated_distributed_systems,
    check_no_fabricated_scalable_software,
    check_no_inflated_architected_verb,
    check_no_inflated_pcb_design_verb,
    check_valid_phone_format,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def bad_amazon_tex() -> str:
    """Load raw LaTeX source of the uncorrected Amazon resume."""
    path = FIXTURES_DIR / "bad_amazon_resume.tex"
    assert path.exists(), f"Missing fixture: {path}"
    return path.read_text(encoding="utf-8")


@pytest.fixture
def good_amazon_tex() -> str:
    """Load raw LaTeX source of the hand-corrected Amazon resume."""
    path = FIXTURES_DIR / "good_amazon_resume.tex"
    assert path.exists(), f"Missing fixture: {path}"
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Individual Check Tests: Verify each check fails on bad, passes on good
# ---------------------------------------------------------------------------

def test_distributed_systems_fabrication_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on ungrounded 'distributed systems' claim and passes on corrected version."""
    passed_bad, reason_bad = check_no_fabricated_distributed_systems(bad_amazon_tex)
    assert not passed_bad, "Check should have caught fabricated 'distributed systems'"
    assert "distributed systems" in reason_bad

    passed_good, reason_good = check_no_fabricated_distributed_systems(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_scalable_software_fabrication_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on ungrounded 'scalable software' claim and passes on corrected version."""
    passed_bad, reason_bad = check_no_fabricated_scalable_software(bad_amazon_tex)
    assert not passed_bad, "Check should have caught fabricated 'scalable software'"
    assert "scalable software" in reason_bad

    passed_good, reason_good = check_no_fabricated_scalable_software(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_architected_verb_inflation_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on inflated 'Architected' lead verb for Asimov Jr. role."""
    passed_bad, reason_bad = check_no_inflated_architected_verb(bad_amazon_tex)
    assert not passed_bad, "Check should have caught inflated 'Architected' verb"

    passed_good, reason_good = check_no_inflated_architected_verb(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_pcb_design_verb_inflation_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on inflated 'Designed multilayer custom PCBs' claim."""
    passed_bad, reason_bad = check_no_inflated_pcb_design_verb(bad_amazon_tex)
    assert not passed_bad, "Check should have caught inflated PCB design claim"

    passed_good, reason_good = check_no_inflated_pcb_design_verb(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_leadership_omission_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails when Asimov Jr. leadership (leading 5+ developers) is omitted."""
    passed_bad, reason_bad = check_leadership_and_team_size_preserved(bad_amazon_tex)
    assert not passed_bad, "Check should have caught omitted leadership scope"

    passed_good, reason_good = check_leadership_and_team_size_preserved(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_phone_format_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on invalid French phone notation (+33 07...) and passes on (+33 7...)."""
    passed_bad, reason_bad = check_valid_phone_format(bad_amazon_tex)
    assert not passed_bad, "Check should have caught invalid phone format"

    passed_good, reason_good = check_valid_phone_format(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_contact_https_scheme_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on hrefs omitting https:// protocol scheme."""
    passed_bad, reason_bad = check_contact_links_have_https_scheme(bad_amazon_tex)
    assert not passed_bad, "Check should have caught contact link without scheme"

    passed_good, reason_good = check_contact_links_have_https_scheme(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_bare_profile_as_project_url_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails on project link pointing to user profile page instead of repository."""
    passed_bad, reason_bad = check_no_bare_profile_as_project_url(bad_amazon_tex)
    assert not passed_bad, "Check should have caught project link pointing to profile"

    passed_good, reason_good = check_no_bare_profile_as_project_url(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


def test_empty_certifications_section_title_check(bad_amazon_tex: str, good_amazon_tex: str) -> None:
    """Check fails when section is titled 'Languages & Certifications' but certifications is empty."""
    passed_bad, reason_bad = check_no_empty_certifications_in_section_title(bad_amazon_tex)
    assert not passed_bad, "Check should have caught empty certifications section title"

    passed_good, reason_good = check_no_empty_certifications_in_section_title(good_amazon_tex)
    assert passed_good, f"Good resume should pass: {reason_good}"


# ---------------------------------------------------------------------------
# Comprehensive Golden Suite Test
# ---------------------------------------------------------------------------

ALL_CHECKS = [
    check_no_fabricated_distributed_systems,
    check_no_fabricated_scalable_software,
    check_no_inflated_architected_verb,
    check_no_inflated_pcb_design_verb,
    check_leadership_and_team_size_preserved,
    check_valid_phone_format,
    check_contact_links_have_https_scheme,
    check_no_bare_profile_as_project_url,
    check_no_empty_certifications_in_section_title,
]


def test_all_checks_pass_on_good_resume(good_amazon_tex: str) -> None:
    """Assert that 100% of golden regression checks pass on the corrected reference resume."""
    failures = []
    for check_func in ALL_CHECKS:
        passed, reason = check_func(good_amazon_tex)
        if not passed:
            failures.append(f"{check_func.__name__}: {reason}")
    assert not failures, f"Good resume failed {len(failures)} checks:\n" + "\n".join(failures)


def test_bad_resume_fails_expected_checks(bad_amazon_tex: str) -> None:
    """Assert that the uncorrected bad resume fails the targeted defect checks."""
    failed_checks = [check_func.__name__ for check_func in ALL_CHECKS if not check_func(bad_amazon_tex)[0]]
    # All 9 checks must detect defects in the uncorrected bad resume
    assert len(failed_checks) == len(ALL_CHECKS), (
        f"Expected all {len(ALL_CHECKS)} checks to fail on bad resume, but only {len(failed_checks)} failed: {failed_checks}"
    )


def test_good_amazon_resume_compiles_to_single_page(tmp_path: Path) -> None:
    """Assert that the corrected Amazon reference resume compiles to exactly 1 page."""
    good_tex_path = FIXTURES_DIR / "good_amazon_resume.tex"
    tectonic_bin = shutil.which("tectonic") or "/home/samuel/.local/bin/tectonic"
    if not Path(tectonic_bin).exists():
        pytest.skip("Tectonic binary not available in test environment")

    # Compile with Tectonic
    proc = subprocess.run(
        [tectonic_bin, str(good_tex_path), "--outdir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"Compilation failed: {proc.stderr}"

    pdf_path = tmp_path / "good_amazon_resume.pdf"
    assert pdf_path.exists(), "Compiled PDF not found"

    # Check page count via pdfinfo if available
    pdfinfo_bin = shutil.which("pdfinfo")
    if pdfinfo_bin:
        info_proc = subprocess.run(
            [pdfinfo_bin, str(pdf_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert info_proc.returncode == 0
        pages_line = [line for line in info_proc.stdout.splitlines() if line.startswith("Pages:")]
        assert pages_line, "Could not determine page count from pdfinfo output"
        num_pages = int(pages_line[0].split(":")[1].strip())
        assert num_pages == 1, f"Expected exactly 1 page, but got {num_pages} pages"
