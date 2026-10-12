"""Deterministic verification of generated resumes (phase P5).

Implements metrics M1a–c, M2, M3, M4 and M5 of ``docs/research_plan.md`` without any
LLM or network call. The claim-level judge (M1d) belongs to phase P6.
"""

from src.verification.coverage import CoverageResult, check_coverage
from src.verification.fabrication import FabricationResult, UnsupportedClaim, check_fabrication
from src.verification.format_checks import FormatCheck, FormatResult, check_format
from src.verification.ground_truth import GroundTruth
from src.verification.inflation import InflatedBullet, InflationResult, check_inflation
from src.verification.issues import VerificationIssue, collect_issues
from src.verification.keywords import KeywordResult, check_keywords
from src.verification.repair import RepairAction, RepairLog, repair_resume
from src.verification.report import VerificationReport, verify_resume
from src.verification.tex_parser import parse_tex_resume

__all__ = [
    "CoverageResult",
    "FabricationResult",
    "FormatCheck",
    "FormatResult",
    "GroundTruth",
    "InflatedBullet",
    "InflationResult",
    "KeywordResult",
    "RepairAction",
    "RepairLog",
    "UnsupportedClaim",
    "VerificationIssue",
    "VerificationReport",
    "check_coverage",
    "check_fabrication",
    "check_format",
    "check_inflation",
    "check_keywords",
    "collect_issues",
    "parse_tex_resume",
    "repair_resume",
    "verify_resume",
]
