"""Automated benchmark pipeline for RAG resume generation quality evaluation.

Orchestrates the full flow:
1. Loading evaluation test cases from YAML (data/eval/evaluation_dataset.yaml)
2. Generating context via KnowledgeBasePipeline (hybrid retrieval)
3. Generating tailored resumes via ResumeGenerationChain (Gemini LLM)
4. Formatting candidate facts and generated resumes into evaluation representations
5. Running EvaluationRunner (faithfulness, answer_relevancy, context_precision)
6. Compiling analytical results into docs/evaluation.md
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from typing import Sequence

from src.config import get_settings
from src.data.candidate import CandidateProfile
from src.data.evaluation import EvaluationDataset, EvaluationTestCase
from src.data.resume import TailoredResume
from src.evaluation.runner import (
    EvaluationRunResult,
    EvaluationRunner,
    EvaluationSample,
    format_evaluation_report,
)
from src.generation.chain import ResumeGenerationChain, get_gemini_llm
from src.retrieval.pipeline import KnowledgeBasePipeline
from src.retrieval.retriever import format_retrieved_context

logger = logging.getLogger(__name__)


def format_candidate_facts(candidate: CandidateProfile) -> str:
    """Format the candidate profile into comprehensive factual prose for evaluation.

    This representation serves as the strict ground truth against which
    the Faithfulness evaluator measures factual grounding and anti-hallucination.

    Args:
        candidate: CandidateProfile containing verified candidate data.

    Returns:
        str: Structured markdown representation of all facts in the candidate profile.
    """
    lines: list[str] = [
        f"# Verified Candidate Background: {candidate.contact.full_name}",
        f"- Email: {candidate.contact.email}",
        f"- Phone: {candidate.contact.phone}",
        f"- Location: {candidate.contact.location}",
    ]
    if candidate.contact.linkedin_url:
        lines.append(f"- LinkedIn: {candidate.contact.linkedin_url}")
    if candidate.contact.github_url:
        lines.append(f"- GitHub: {candidate.contact.github_url}")

    if candidate.summary:
        lines.append(f"\n## Summary / Bio:\n{candidate.summary.strip()}")

    lines.append("\n## Education:")
    for edu in candidate.education:
        curr_str = " (Current)" if edu.current else ""
        lines.append(f"- {edu.degree} at {edu.institution} ({edu.start_date} - {edu.end_date}){curr_str}")
        if edu.gpa_or_honors:
            lines.append(f"  * Honors/GPA: {edu.gpa_or_honors}")
        if edu.relevant_coursework:
            lines.append(f"  * Coursework: {', '.join(edu.relevant_coursework)}")
        if edu.highlights:
            for hl in edu.highlights:
                lines.append(f"  * Highlight: {hl}")

    lines.append("\n## Experiences:")
    for exp in candidate.experiences:
        curr_str = " (Current)" if exp.current else ""
        loc_str = f" [{exp.location}]" if exp.location else ""
        lines.append(f"- {exp.title} at {exp.organization}{loc_str} ({exp.start_date} - {exp.end_date}){curr_str}")
        for b in exp.bullets:
            lines.append(f"  * {b}")
        if exp.technologies:
            lines.append(f"  * Technologies: {', '.join(exp.technologies)}")

    lines.append("\n## Projects:")
    for proj in candidate.projects:
        lines.append(f"- Project: {proj.name}")
        lines.append(f"  * Description: {proj.description}")
        for b in proj.bullets:
            lines.append(f"  * {b}")
        if proj.technologies:
            lines.append(f"  * Technologies: {', '.join(proj.technologies)}")

    lines.append("\n## Technical and Soft Skills:")
    lines.append(f"- Languages: {', '.join(candidate.skills.programming_languages)}")
    lines.append(f"- Frameworks: {', '.join(candidate.skills.frameworks_and_libraries)}")
    lines.append(f"- Databases: {', '.join(candidate.skills.databases)}")
    lines.append(f"- Tools: {', '.join(candidate.skills.tools_and_platforms)}")
    lines.append(f"- Soft Skills: {', '.join(candidate.skills.soft_skills)}")

    if candidate.languages:
        lines.append("\n## Spoken/Written Languages:")
        for lang in candidate.languages:
            lines.append(f"- {lang.language}: {lang.proficiency}")

    if candidate.certifications:
        lines.append("\n## Certifications:")
        for cert in candidate.certifications:
            lines.append(f"- {cert.name} ({cert.issuer}, {cert.issue_date})")

    if candidate.additional_info:
        lines.append("\n## Additional Information:")
        for info in candidate.additional_info:
            lines.append(f"- {info}")

    return "\n".join(lines)


def format_resume_as_text(resume: TailoredResume) -> str:
    """Convert TailoredResume structured model into plain text for evaluation.

    Args:
        resume: Generated TailoredResume instance.

    Returns:
        str: Comprehensive textual representation of the resume.
    """
    lines: list[str] = [
        f"RESUME FOR: {resume.header.full_name}",
        f"TARGET: {resume.target_job_title} @ {resume.target_company}",
        f"EMAIL: {resume.header.email} | LOCATION: {resume.header.location}",
    ]

    if resume.objective_or_summary:
        lines += ["", "PROFESSIONAL OBJECTIVE:", resume.objective_or_summary]

    lines += ["", "EDUCATION:"]
    for edu in resume.education:
        lines.append(f"- {edu.degree} - {edu.institution} ({edu.period})")
        for hl in edu.highlights:
            lines.append(f"  * {hl}")

    lines.append("\nEXPERIENCE:")
    for exp in resume.experiences:
        lines.append(f"- {exp.title} - {exp.organization} ({exp.period})")
        for b in exp.bullets:
            lines.append(f"  * {b}")
        if exp.technologies:
            lines.append(f"  Technologies: {', '.join(exp.technologies)}")

    lines.append("\nPROJECTS:")
    for proj in resume.projects:
        lines.append(f"- {proj.name}")
        for b in proj.bullets:
            lines.append(f"  * {b}")
        if proj.technologies:
            lines.append(f"  Technologies: {', '.join(proj.technologies)}")

    lines.append("\nSKILLS:")
    for cat in resume.skills:
        lines.append(f"- {cat.category_name}: {', '.join(cat.skills)}")

    if resume.languages:
        lines.append("\nLANGUAGES:")
        for l in resume.languages:
            lines.append(f"- {l.language}: {l.proficiency}")

    return "\n".join(lines)


def format_resume_claims(resume: TailoredResume) -> str:
    """Extract factual credentials and claims from the resume for faithfulness evaluation.

    Focuses strictly on the candidate's stated qualifications (education, experiences,
    projects, skills, languages, certifications), excluding application metadata like the
    target company or job title which are not part of the candidate's historical background.

    Args:
        resume: Generated TailoredResume instance.

    Returns:
        str: Text containing only factual candidate claims to verify.
    """
    lines: list[str] = ["CANDIDATE CLAIMS IN RESUME:"]
    for edu in resume.education:
        lines.append(f"- Education: {edu.degree} at {edu.institution} ({edu.period}). Highlights: {', '.join(edu.highlights)}")
    for exp in resume.experiences:
        lines.append(f"- Experience: {exp.title} at {exp.organization} ({exp.period}). Bullets: {' '.join(exp.bullets)}. Technologies: {', '.join(exp.technologies)}")
    for proj in resume.projects:
        lines.append(f"- Project: {proj.name}. Bullets: {' '.join(proj.bullets)}. Technologies: {', '.join(proj.technologies)}")
    for cat in resume.skills:
        lines.append(f"- Skills ({cat.category_name}): {', '.join(cat.skills)}")
    if resume.languages:
        for l in resume.languages:
            lines.append(f"- Language: {l.language} ({l.proficiency})")
    if resume.certifications:
        for cert in resume.certifications:
            lines.append(f"- Certification: {cert}")
    return "\n".join(lines)


class EvaluationBenchmark:
    """Benchmark orchestrator for executing and scoring resume generation runs."""

    def __init__(
        self,
        pipeline: KnowledgeBasePipeline | None = None,
        chain: ResumeGenerationChain | None = None,
        runner: EvaluationRunner | None = None,
    ) -> None:
        """Initialize benchmark with optional dependency injection.

        Args:
            pipeline: KnowledgeBasePipeline for retrieval. Defaults to a new instance.
            chain: ResumeGenerationChain for LLM generation. Defaults to Gemini chain.
            runner: EvaluationRunner for scoring. Defaults to Gemini-backed runner.
        """
        self._pipeline = pipeline
        self._chain = chain
        self._runner = runner

    def _get_pipeline(self) -> KnowledgeBasePipeline:
        if self._pipeline is None:
            self._pipeline = KnowledgeBasePipeline()
        return self._pipeline

    def _get_chain(self) -> ResumeGenerationChain:
        if self._chain is None:
            llm = get_gemini_llm()
            self._chain = ResumeGenerationChain(llm=llm)
        return self._chain

    def _get_runner(self) -> EvaluationRunner:
        if self._runner is None:
            llm = get_gemini_llm()
            self._runner = EvaluationRunner(llm=llm)
        return self._runner

    def run_test_case(
        self,
        test_case: EvaluationTestCase,
        candidate: CandidateProfile,
        top_k: int = 5,
    ) -> EvaluationRunResult:
        """Run retrieval, generation, and evaluation for a single test case.

        Args:
            test_case: EvaluationTestCase to process.
            candidate: CandidateProfile ground truth.
            top_k: Number of knowledge chunks to retrieve.

        Returns:
            EvaluationRunResult containing scores and feedback.
        """
        job = test_case.to_job_posting()
        pipeline = self._get_pipeline()
        chain = self._get_chain()
        runner = self._get_runner()

        logger.info("Executing retrieval for '%s @ %s'...", job.title, job.company)
        retrieved_nodes = pipeline.retrieve_for_job(job=job, top_k=top_k)
        retrieved_contexts = [n.node.get_content() for n in retrieved_nodes]
        guidelines_str = format_retrieved_context(retrieved_nodes)

        logger.info("Generating tailored resume with LLM chain...")
        tailored_resume = chain.generate(
            candidate=candidate,
            job=job,
            retrieved_guidelines=guidelines_str,
        )

        response_text = format_resume_as_text(tailored_resume)
        claims_text = format_resume_claims(tailored_resume)
        candidate_facts_text = format_candidate_facts(candidate)

        sample = EvaluationSample(
            query=job.to_search_query(),
            retrieved_contexts=retrieved_contexts,
            generated_response=response_text,
            candidate_facts=candidate_facts_text,
            job_title=job.title,
            company=job.company,
            faithfulness_claim=claims_text,
        )

        logger.info("Scoring sample with evaluation runner...")
        return runner.evaluate_sample(sample)

    def run_benchmark(
        self,
        dataset: EvaluationDataset,
        candidate: CandidateProfile,
        top_k: int = 5,
        test_case_ids: Sequence[str] | None = None,
    ) -> list[EvaluationRunResult]:
        """Execute the benchmark over all or selected test cases.

        Args:
            dataset: EvaluationDataset with test cases.
            candidate: CandidateProfile ground truth.
            top_k: Number of retrieved chunks per query.
            test_case_ids: Optional list of test case IDs to filter.

        Returns:
            list[EvaluationRunResult]: Ordered evaluation outcomes.
        """
        cases = dataset.test_cases
        if test_case_ids:
            cases = [tc for tc in cases if tc.id in test_case_ids]

        logger.info("Starting benchmark run over %d test cases...", len(cases))
        results: list[EvaluationRunResult] = []

        for idx, tc in enumerate(cases, start=1):
            logger.info("[%d/%d] Running benchmark for: %s", idx, len(cases), tc.id)
            result = self.run_test_case(tc, candidate=candidate, top_k=top_k)
            results.append(result)
            if idx < len(cases):
                time.sleep(3.0)

        return results

    @staticmethod
    def save_report(
        results: list[EvaluationRunResult],
        output_path: Path | str = "docs/evaluation.md",
    ) -> str:
        """Format and write the evaluation report to disk.

        Args:
            results: List of evaluated run outcomes.
            output_path: Destination path for the report.

        Returns:
            str: Generated markdown report content.
        """
        report_md = format_evaluation_report(results)
        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(report_md, encoding="utf-8")
        logger.info("Saved evaluation report to: %s", dest)
        return report_md


def main() -> None:
    """CLI entrypoint for running the evaluation benchmark."""
    parser = argparse.ArgumentParser(description="Run RAG Resume Generator evaluation benchmark.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="data/eval/evaluation_dataset.yaml",
        help="Path to evaluation dataset YAML file.",
    )
    parser.add_argument(
        "--candidate",
        type=str,
        default="data/candidate_profile.yaml",
        help="Path to candidate profile YAML.",
    )
    parser.add_argument(
        "--cases",
        type=str,
        default=None,
        help="Comma-separated test case IDs to evaluate (e.g. 'genai_rag_intern,backend_python_intern').",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Top-k retrieval chunks.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="docs/evaluation.md",
        help="Path to save the generated markdown evaluation report.",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    dataset = EvaluationDataset.from_yaml(args.dataset)
    candidate = CandidateProfile.from_yaml(args.candidate)

    case_ids = [c.strip() for c in args.cases.split(",")] if args.cases else None

    benchmark = EvaluationBenchmark()
    results = benchmark.run_benchmark(
        dataset=dataset,
        candidate=candidate,
        top_k=args.top_k,
        test_case_ids=case_ids,
    )
    report = benchmark.save_report(results, output_path=args.output)
    print("\n" + report)


if __name__ == "__main__":
    main()
