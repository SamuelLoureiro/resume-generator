"""Deterministic verification checks for Phase B defect prevention.

Implements:
- B1: SUMMARY_LINT (forbidden meta-words in free text)
- B2: JOB_PHRASE_ECHO (n-gram echoing of job posting phrases)
- B3: FACT_FUSION (sentence multi-fact fusion detection)
- B5: SUMMARY_VERB (M2 verb ladder applied across all candidate verbs in summary)
"""

from __future__ import annotations

import re
from typing import Any

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts
from src.data.job_posting import JobPosting
from src.data.resume import TailoredResume
from src.verification.matching import (
    DEFAULT_MATCH_THRESHOLD,
    similarity,
)
from src.verification.text_utils import tokenize


def bullet_id_for(section: str, entry_index: int, bullet_index: int) -> str:
    """Build the canonical bullet id."""
    prefix = "exp" if section == "experience" else "proj"
    return f"{prefix}_{entry_index}_bullet_{bullet_index}"
from src.verification.verb_ladder import (
    DESIGN_VERBS,
    VERB_LEVELS,
    _ALL_PHRASES,
    _MAX_PHRASE_WORDS,
    _WORD_RE,
    design_evidence_in,
    verb_words,
)

# B1 Forbidden meta-words (pipeline vocabulary leaks)
FORBIDDEN_META_WORDS: tuple[str, ...] = (
    "verified",
    "validated by",
    "grounded",
    "fact",
    "ceiling",
    "pipeline",
    "llm",
    "rag-verified",
)

# Common multilingual stopwords for n-gram echoing (EN, PT, FR)
STOPWORDS: frozenset[str] = frozenset(
    {
        # English
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
        "are", "as", "at", "be", "because", "been", "before", "being", "below", "between",
        "both", "but", "by", "can", "did", "do", "does", "doing", "down", "during", "each",
        "few", "for", "from", "further", "had", "has", "have", "having", "he", "her", "here",
        "hers", "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it",
        "its", "itself", "just", "me", "more", "most", "my", "myself", "no", "nor", "not",
        "now", "of", "off", "on", "once", "only", "or", "other", "our", "ours", "ourselves",
        "out", "over", "own", "same", "she", "should", "so", "some", "such", "than", "that",
        "the", "their", "theirs", "them", "themselves", "then", "there", "these", "they", "this",
        "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were",
        "what", "when", "where", "which", "while", "who", "whom", "why", "with", "would", "you",
        "your", "yours", "yourself", "yourselves",
        # Portuguese
        "de", "a", "o", "que", "e", "do", "da", "em", "um", "para", "é", "com", "não", "uma",
        "os", "no", "se", "na", "por", "mais", "as", "dos", "como", "mas", "foi", "ao", "ele",
        "das", "tem", "à", "seu", "sua", "ou", "ser", "quando", "muito", "nos", "já", "eu",
        "também", "só", "pelo", "pela", "até", "isso", "ela", "entre", "era", "depois", "sem",
        "mesmo", "aos", "ter", "seus", "quem", "nas", "me", "esse", "eles", "estão", "você",
        # French
        "le", "la", "les", "de", "des", "du", "un", "une", "et", "est", "en", "que", "qui",
        "dans", "pour", "par", "sur", "au", "aux", "avec", "ce", "ces", "cette", "mais", "ou",
        "donc", "or", "ni", "car", "se", "sa", "son", "ses", "leur", "leurs", "nous", "vous",
        "ils", "elles", "mon", "ma", "mes", "ton", "ta", "tes", "tout", "tous", "toute", "toutes",
    }
)


def _split_into_sentences(text: str) -> list[str]:
    """Split free text into non-empty sentences."""
    if not text:
        return []
    # Split on sentence ending punctuation followed by whitespace or line break
    raw_sents = re.split(r"(?<=[.!?])\s+", text.strip())
    return [s.strip() for s in raw_sents if s.strip()]


def _extract_profile_allowlist_tokens(profile: CandidateProfile) -> set[str]:
    """Extract allowlisted words from profile projects, skills, and certifications."""
    tokens: set[str] = set()
    for p in profile.projects:
        tokens.update(tokenize(p.name.lower()))
        for t in p.technologies:
            tokens.update(tokenize(t.lower()))
    for exp in profile.experiences:
        for t in exp.technologies:
            tokens.update(tokenize(t.lower()))
    for cat in (
        profile.skills.programming_languages
        + profile.skills.frameworks_and_libraries
        + profile.skills.databases
        + profile.skills.tools_and_platforms
    ):
        tokens.update(tokenize(cat.lower()))
    return tokens


def check_summary_lint(
    resume: TailoredResume,
    profile: CandidateProfile,
) -> list[dict[str, Any]]:
    """B1: Check for forbidden meta-words in any free text (summary and bullets).

    Args:
        resume: Structured resume under verification.
        profile: Candidate profile source of truth (provides tech/project exemptions).

    Returns:
        list[dict[str, Any]]: Detected meta-word issues.
    """
    allowlist = _extract_profile_allowlist_tokens(profile)
    issues: list[dict[str, Any]] = []

    def _scan_text(text: str, location: str) -> None:
        if not text:
            return
        for forbidden in FORBIDDEN_META_WORDS:
            # Plural / variation regex: e.g. "verified", "facts", "pipelines", "LLMs"
            pattern = re.compile(
                r"\b" + re.escape(forbidden) + r"(?:s|ed|ing|d)?\b",
                re.IGNORECASE,
            )
            for m in pattern.finditer(text):
                match_str = m.group(0)
                # Check if exact match token is in profile allowlist
                if match_str.lower() in allowlist:
                    continue
                issues.append(
                    {
                        "kind": "summary_lint",
                        "source": "deterministic",
                        "location": location,
                        "text": match_str,
                        "detail": (
                            f"Forbidden meta-word '{match_str}' found in free text "
                            "(internal pipeline vocabulary leak)."
                        ),
                        "check": "B1/summary_lint",
                        "llm_fixable": True,
                    }
                )

    if resume.objective_or_summary:
        _scan_text(resume.objective_or_summary, "summary")

    for e_idx, exp in enumerate(resume.experiences):
        for b_idx, bullet in enumerate(exp.bullets):
            loc = bullet_id_for("experience", e_idx, b_idx)
            _scan_text(bullet, loc)

    for p_idx, proj in enumerate(resume.projects):
        for b_idx, bullet in enumerate(proj.bullets):
            loc = bullet_id_for("project", p_idx, b_idx)
            _scan_text(bullet, loc)

    return issues


def _extract_content_words(text: str) -> list[str]:
    """Tokenize text into lowercase words excluding stopwords."""
    words = re.findall(r"[\w'’+\-]+", text.lower(), re.UNICODE)
    return [w for w in words if w not in STOPWORDS and len(w) > 1]


def _build_ngrams(words: list[str], n: int = 3) -> set[tuple[str, ...]]:
    """Build n-grams of specified size from a list of words."""
    if len(words) < n:
        return set()
    return {tuple(words[i : i + n]) for i in range(len(words) - n + 1)}


def check_job_phrase_echo(
    resume: TailoredResume,
    job: JobPosting,
    profile: CandidateProfile,
    facts: CandidateFacts,
) -> list[dict[str, Any]]:
    """B2: Detect n-grams (n>=3) echoed verbatim from job posting not grounded in candidate facts.

    Exempts allowlisted skill and technology names.

    Args:
        resume: Structured resume under verification.
        job: Target job posting.
        profile: Candidate profile source of truth.
        facts: Verified candidate atomic facts.

    Returns:
        list[dict[str, Any]]: Detected verbatim echo issues.
    """
    # Build job corpus from description, responsibilities, requirements, techs, keywords
    job_corpus = " ".join(
        [
            job.raw_description,
            " ".join(job.responsibilities),
            " ".join(job.requirements),
            " ".join(job.technologies),
            " ".join(job.keywords),
        ]
    )
    job_words = _extract_content_words(job_corpus)
    job_trigrams = _build_ngrams(job_words, n=3)

    # Title and company n-grams are valid application target metadata and are exempted
    title_company_words = _extract_content_words(f"{job.title} {job.company}")
    title_company_trigrams = _build_ngrams(title_company_words, n=3)
    job_trigrams -= title_company_trigrams

    if not job_trigrams:
        return []

    # Build candidate grounded corpus (facts text + profile bullets/degrees/skills)
    cand_parts: list[str] = [f.text for f in facts.facts]
    for exp in profile.experiences:
        cand_parts.extend(exp.bullets)
        cand_parts.extend(exp.technologies)
    for proj in profile.projects:
        cand_parts.extend(proj.bullets)
        cand_parts.extend(proj.technologies)
    for edu in profile.education:
        cand_parts.append(edu.degree)
        cand_parts.extend(edu.relevant_coursework)
        cand_parts.extend(edu.highlights)
    cand_parts.extend(
        profile.skills.programming_languages
        + profile.skills.frameworks_and_libraries
        + profile.skills.databases
        + profile.skills.tools_and_platforms
    )
    cand_corpus = " ".join(cand_parts)
    cand_words = _extract_content_words(cand_corpus)
    cand_trigrams = _build_ngrams(cand_words, n=3)

    # Allowlisted skill phrases (multi-word technologies)
    skill_allowlist: set[str] = {
        s.lower().strip()
        for s in (
            profile.skills.programming_languages
            + profile.skills.frameworks_and_libraries
            + profile.skills.databases
            + profile.skills.tools_and_platforms
        )
    }

    issues: list[dict[str, Any]] = []

    def _check_sentence(sent: str, location: str) -> None:
        sent_words = _extract_content_words(sent)
        sent_trigrams = _build_ngrams(sent_words, n=3)
        for tri in sent_trigrams:
            if tri in job_trigrams and tri not in cand_trigrams:
                phrase = " ".join(tri)
                if phrase in skill_allowlist:
                    continue
                issues.append(
                    {
                        "kind": "job_phrase_echo",
                        "source": "deterministic",
                        "location": location,
                        "text": phrase,
                        "detail": (
                            f"Phrase '{phrase}' echoes the job posting verbatim without grounding "
                            "in candidate facts; rewrite using candidate's own fact wording."
                        ),
                        "check": "B2/job_phrase_echo",
                        "llm_fixable": True,
                    }
                )

    if resume.objective_or_summary:
        for s in _split_into_sentences(resume.objective_or_summary):
            _check_sentence(s, "summary")

    for e_idx, exp in enumerate(resume.experiences):
        for b_idx, bullet in enumerate(exp.bullets):
            loc = bullet_id_for("experience", e_idx, b_idx)
            for s in _split_into_sentences(bullet):
                _check_sentence(s, loc)

    for p_idx, proj in enumerate(resume.projects):
        for b_idx, bullet in enumerate(proj.bullets):
            loc = bullet_id_for("project", p_idx, b_idx)
            for s in _split_into_sentences(bullet):
                _check_sentence(s, loc)

    # De-duplicate issues at same location with same text
    unique_issues: list[dict[str, Any]] = []
    seen = set()
    for iss in issues:
        key = (iss["location"], iss["text"])
        if key not in seen:
            seen.add(key)
            unique_issues.append(iss)
    return unique_issues


# Distinctive entity/keyword markers for known multi-fact fusion detection
FACT_DISTINCTIVE_MARKERS: dict[str, list[str]] = {
    "exp_asimov_leadership": [
        "data science department",
        "data science dept",
        "5+ developers",
        "5+ devs",
        "mobile area manager",
    ],
    "exp_asimov_mobile_area_of_month": [
        "area of the month",
        "area do mês",
        "top-performing",
        "mobile team to win",
    ],
    "exp_asimov_member_of_month": [
        "member of the month",
        "membro do mês",
        "individual performance",
        "individual distinction",
    ],
}


def check_fact_fusion(
    resume: TailoredResume,
    facts: CandidateFacts,
    threshold: float = 0.32,
) -> list[dict[str, Any]]:
    """B3: Detect fact fusion where a single sentence combines claims from distinct atomic facts.

    Every sentence and bullet must map to exactly ONE atomic fact. If a sentence
    has top-2 fact matches above threshold or combines distinct markers from two facts
    (e.g. Asimov leadership Data Science dept + Area of the Month), emit FACT_FUSION.

    Args:
        resume: Structured resume under verification.
        facts: Verified candidate atomic facts.
        threshold: Minimum Dice similarity threshold for secondary fact matching.

    Returns:
        list[dict[str, Any]]: Detected fact fusion defects.
    """
    issues: list[dict[str, Any]] = []

    def _check_sentence(sent: str, location: str) -> None:
        clean_s = sent.strip()
        if len(clean_s.split()) < 4:
            return
        lowered = clean_s.lower()

        # 1. Distinctive cross-fact entity marker detection (e.g. Asimov Leadership + Awards)
        matched_marker_facts: set[str] = set()
        for fid, markers in FACT_DISTINCTIVE_MARKERS.items():
            if any(m in lowered for m in markers):
                matched_marker_facts.add(fid)

        # Specifically detect leadership + area of month / member of month fusion
        if "exp_asimov_leadership" in matched_marker_facts and (
            "exp_asimov_mobile_area_of_month" in matched_marker_facts
            or "exp_asimov_member_of_month" in matched_marker_facts
        ):
            other_fid = (
                "exp_asimov_mobile_area_of_month"
                if "exp_asimov_mobile_area_of_month" in matched_marker_facts
                else "exp_asimov_member_of_month"
            )
            issues.append(
                {
                    "kind": "fact_fusion",
                    "source": "deterministic",
                    "location": location,
                    "text": clean_s,
                    "detail": (
                        f"Fused facts 'exp_asimov_leadership' and '{other_fid}': "
                        "Split into two sentences or keep only one fact; "
                        "keep subject nouns (team/department/area) attached to the fact they come from."
                    ),
                    "fact_id": f"exp_asimov_leadership,{other_fid}",
                    "check": "B3/fact_fusion",
                    "llm_fixable": True,
                }
            )
            return

        # 2. General top-2 fact similarity scoring
        scores: list[tuple[float, str]] = []
        for f in facts.facts:
            sim = similarity(clean_s, f.text)
            if sim >= threshold:
                scores.append((sim, f.id))
        scores.sort(reverse=True)

        if len(scores) >= 2:
            s1, f1 = scores[0]
            s2, f2 = scores[1]
            if f1 != f2 and s2 >= threshold and (s1 - s2) <= 0.08:
                issues.append(
                    {
                        "kind": "fact_fusion",
                        "source": "deterministic",
                        "location": location,
                        "text": clean_s,
                        "detail": (
                            f"Fused facts '{f1}' and '{f2}': "
                            "Split into two sentences or keep only one fact; "
                            "keep subject nouns (team/department/area) attached to the fact they come from."
                        ),
                        "fact_id": f"{f1},{f2}",
                        "check": "B3/fact_fusion",
                        "llm_fixable": True,
                    }
                )

    if resume.objective_or_summary:
        for s in _split_into_sentences(resume.objective_or_summary):
            _check_sentence(s, "summary")

    for e_idx, exp in enumerate(resume.experiences):
        for b_idx, bullet in enumerate(exp.bullets):
            loc = bullet_id_for("experience", e_idx, b_idx)
            for s in _split_into_sentences(bullet):
                _check_sentence(s, loc)

    for p_idx, proj in enumerate(resume.projects):
        for b_idx, bullet in enumerate(proj.bullets):
            loc = bullet_id_for("project", p_idx, b_idx)
            for s in _split_into_sentences(bullet):
                _check_sentence(s, loc)

    return issues


def check_summary_verbs(
    resume: TailoredResume,
    facts: CandidateFacts,
    threshold: float = 0.25,
) -> list[dict[str, Any]]:
    """B5: Apply the M2 verb ladder to every candidate verb in the summary.

    Verifies that no verb attributed to the candidate exceeds the scope ceiling
    of the nearest matched atomic fact.

    Args:
        resume: Structured resume under verification.
        facts: Verified candidate atomic facts.
        threshold: Minimum similarity threshold to associate summary sentence with a fact.

    Returns:
        list[dict[str, Any]]: Detected inflated verb issues in the summary.
    """
    if not resume.objective_or_summary:
        return []

    issues: list[dict[str, Any]] = []
    sentences = _split_into_sentences(resume.objective_or_summary)

    for sent in sentences:
        clean_s = sent.strip()
        words = [w.lower() for w in _WORD_RE.findall(clean_s)]
        if not words:
            continue

        # Find best matching fact for this summary sentence
        best_fact = None
        best_sim = 0.0
        for f in facts.facts:
            sim = similarity(clean_s, f.text)
            if sim > best_sim:
                best_sim = sim
                best_fact = f

        if best_fact is None or best_sim < threshold:
            continue

        matched_fact_words = verb_words(best_fact.text)
        has_design_evidence = design_evidence_in(best_fact.text)

        # Scan all n-word windows for verb ladder matches
        for i in range(len(words)):
            for size in range(min(_MAX_PHRASE_WORDS, len(words) - i), 0, -1):
                phrase = " ".join(words[i : i + size])
                if phrase in _ALL_PHRASES:
                    is_design = phrase in DESIGN_VERBS
                    base_level = _ALL_PHRASES[phrase]
                    # If design verb without design evidence, level is elevated
                    if is_design and not has_design_evidence:
                        effective_level = 4
                    else:
                        effective_level = base_level

                    # If exact phrase is in matched fact text, it is grounded verbatim
                    if phrase in matched_fact_words or any(w in matched_fact_words for w in phrase.split()):
                        continue

                    if effective_level > best_fact.scope_ceiling:
                        issues.append(
                            {
                                "kind": "inflated_verb",
                                "source": "deterministic",
                                "location": "summary",
                                "text": phrase,
                                "detail": (
                                    f"Verb '{phrase}' (level {effective_level}) in summary exceeds "
                                    f"scope ceiling (level {best_fact.scope_ceiling}) of matched fact '{best_fact.id}'."
                                ),
                                "fact_id": best_fact.id,
                                "scope_ceiling": best_fact.scope_ceiling,
                                "check": "B5/summary_verb",
                                "llm_fixable": True,
                            }
                        )

    return issues
