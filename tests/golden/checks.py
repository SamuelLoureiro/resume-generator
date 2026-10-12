"""Verification rules and checks for the golden regression test suite.

Each check tests a specific known defect identified in docs/audit_report.md
to guarantee that regressions do not return.
"""

from __future__ import annotations

import re


def check_no_fabricated_distributed_systems(tex_content: str) -> tuple[bool, str]:
    """Check that 'distributed systems' is not claimed unless supported by profile facts."""
    match = re.search(r"distributed\s+systems", tex_content, re.IGNORECASE)
    if match:
        return False, "Found unsupported claim 'distributed systems' in resume"
    return True, "No fabricated 'distributed systems' claim found"


def check_no_fabricated_scalable_software(tex_content: str) -> tuple[bool, str]:
    """Check that 'scalable cross-platform software' is not claimed without ground truth."""
    match = re.search(r"scalable\s+(cross-platform\s+)?software", tex_content, re.IGNORECASE)
    if match:
        return False, "Found unsupported claim 'scalable software' in resume"
    return True, "No fabricated 'scalable software' claim found"


def check_no_inflated_architected_verb(tex_content: str) -> tuple[bool, str]:
    """Check that Asimov Jr. mobile development role does not inflate verb to 'Architected'."""
    # Look for Architected in experience bullet points
    match = re.search(r"\\item\s+.*Architected.*mobile", tex_content, re.IGNORECASE)
    if match:
        return False, "Found inflated lead verb 'Architected' for Asimov Jr. role"
    return True, "No inflated 'Architected' verb found for Asimov Jr."


def check_no_inflated_pcb_design_verb(tex_content: str) -> tuple[bool, str]:
    """Check that ENIB embedded project does not inflate PCB contribution to lead design."""
    match = re.search(r"\\item\s+.*Designed\s+multilayer\s+custom\s+PCBs", tex_content, re.IGNORECASE)
    if match:
        return False, "Found inflated verb 'Designed multilayer custom PCBs' instead of 'Participated in PCB design'"
    return True, "No inflated PCB design claim found"


def check_leadership_and_team_size_preserved(tex_content: str) -> tuple[bool, str]:
    """Check that candidate's real team leadership at Asimov Jr. (5+ developers) is not omitted."""
    has_developers = bool(re.search(r"5\+\s*developers", tex_content, re.IGNORECASE))
    has_lead = bool(re.search(r"(leading|lead|manager|managed)", tex_content, re.IGNORECASE))
    if not (has_developers and has_lead):
        return False, "Omitted Asimov Jr. leadership scope ('5+ developers' or management not found)"
    return True, "Asimov Jr. leadership scope preserved"


def check_valid_phone_format(tex_content: str) -> tuple[bool, str]:
    """Check that French international phone number does not have invalid leading zero (+33 07...)."""
    match = re.search(r"\+33\s+0[1-9]", tex_content)
    if match:
        return False, f"Invalid French international phone format found: '{match.group(0)}'"
    return True, "Phone number format is valid"


def check_contact_links_have_https_scheme(tex_content: str) -> tuple[bool, str]:
    """Check that href links in header use explicit https:// scheme to avoid relative path errors."""
    # Search for \href{linkedin.com or \href{github.com without https://
    invalid_links = re.findall(r"\\href\{(?!https?://|mailto:)[^}]+\}", tex_content)
    # Check specifically if LinkedIn or GitHub links omit protocol
    bad_domain_links = [link for link in invalid_links if "linkedin.com" in link or "github.com" in link]
    if bad_domain_links:
        return False, f"Found contact link(s) without protocol scheme: {bad_domain_links}"
    return True, "All contact links have valid protocol schemes"


def check_no_bare_profile_as_project_url(tex_content: str) -> tuple[bool, str]:
    """Check that project repository links do not point to a bare user profile."""
    # Specifically check if a project link ([View Project / Code] or [Ver Projeto]) points to a top-level user profile
    match = re.search(r"\\href\{https?://github\.com/[^/]+\/?\}\{\s*\[View Project", tex_content, re.IGNORECASE)
    if match:
        return False, "Found project link pointing to user profile instead of a specific repository"
    return True, "No bare user profile used as project repository link"


def check_no_empty_certifications_in_section_title(tex_content: str) -> tuple[bool, str]:
    """Check that section title is 'Languages' when certifications list is empty."""
    match = re.search(r"\\section\{Languages\s*\\&\s*Certifications\}", tex_content)
    if match:
        # Check if certifications items are actually present
        has_cert_items = bool(re.search(r"\\textbf\{Certifications:\}", tex_content))
        if not has_cert_items:
            return False, "Section titled 'Languages & Certifications' but no certifications are listed"
    return True, "Languages & Certifications title matches content"
