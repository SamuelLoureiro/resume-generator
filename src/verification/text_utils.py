"""Deterministic text normalisation helpers shared by all verification checks.

Everything here is pure string processing: no network, no LLM, no randomness.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

_TOKEN_RE = re.compile(r"[a-z0-9+#]+")
_TERM_SPLIT_RE = re.compile(r"[/,()&;]|\band\b|\be\b|\bet\b", re.IGNORECASE)

# Function words that carry no claim content. Used when comparing bullets to facts.
STOPWORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "of", "for", "to", "in", "on", "at", "by", "with",
        "from", "into", "across", "using", "via", "as", "its", "their", "that", "which",
        "while", "through", "over", "under", "per", "this", "these", "those", "is", "are",
        "was", "were", "be", "been", "being", "it", "within", "between", "all", "new",
        "real", "time",
    }
)


def stem_token(token: str) -> str:
    """Strip a trailing plural 's' so 'APIs' and 'API' compare equal.

    The stem is only used for comparison, never displayed. It is applied
    symmetrically to both sides of every comparison, so over-stemming
    ('analysis' -> 'analysi') is harmless.

    Args:
        token: Lowercase alphanumeric token.

    Returns:
        str: Token without a trailing plural 's' (tokens of length <= 3 are kept).
    """
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokenize(text: str) -> list[str]:
    """Lowercase ``text`` and split it into stemmed alphanumeric tokens.

    ``+`` and ``#`` are kept so that ``C++`` and ``C#`` stay distinct from ``C``.

    Args:
        text: Arbitrary text.

    Returns:
        list[str]: Stemmed tokens in order of appearance.
    """
    return [stem_token(tok) for tok in _TOKEN_RE.findall((text or "").lower())]


def term_key(term: str) -> str:
    """Return a separator-insensitive comparison key for a skill or keyword.

    ``"Scikit-Learn"``, ``"scikit learn"`` and ``"scikitlearn"`` share a key, as
    do ``"ROS 2"`` and ``"ros2"``.

    Args:
        term: Skill, technology or keyword string.

    Returns:
        str: Concatenation of the stemmed tokens (empty string if no token).
    """
    return "".join(tokenize(term))


def split_terms(item: str) -> list[str]:
    """Split a composite skill string into its atomic terms.

    ``"Python (Pandas, NumPy)"`` -> ``["Python", "Pandas", "NumPy"]``;
    ``"C / C++"`` -> ``["C", "C++"]``.

    Args:
        item: Skill or technology string as written in a resume or profile.

    Returns:
        list[str]: Non-empty stripped terms.
    """
    parts = [p.strip() for p in _TERM_SPLIT_RE.split(item or "")]
    return [p for p in parts if p]


def term_keys(items: Iterable[str]) -> set[str]:
    """Return the set of non-empty term keys of every atomic term in ``items``."""
    keys: set[str] = set()
    for item in items:
        for part in split_terms(item):
            key = term_key(part)
            if key:
                keys.add(key)
    return keys


def ngram_keys(text: str, max_n: int = 4) -> set[str]:
    """Return concatenated keys of all 1..``max_n``-grams of ``text``.

    Lets a multi-word term such as ``"ROS 2"`` or ``"REST API"`` be located in
    free text by comparing ``term_key(term)`` against this set.

    Args:
        text: Free text.
        max_n: Longest n-gram to produce.

    Returns:
        set[str]: Keys comparable with :func:`term_key`.
    """
    tokens = tokenize(text)
    keys: set[str] = set()
    for n in range(1, max_n + 1):
        for i in range(len(tokens) - n + 1):
            keys.add("".join(tokens[i : i + n]))
    return keys


def content_tokens(text: str) -> set[str]:
    """Return the set of stemmed tokens of ``text`` excluding stopwords and bare digits."""
    return {t for t in tokenize(text) if t not in STOPWORDS and not t.isdigit() and len(t) > 1}


def similarity(a: str, b: str) -> float:
    """Dice coefficient over content tokens of two strings.

    Args:
        a: First text.
        b: Second text.

    Returns:
        float: Value in [0, 1]; 0.0 if either text has no content tokens.
    """
    ta, tb = content_tokens(a), content_tokens(b)
    if not ta or not tb:
        return 0.0
    return 2 * len(ta & tb) / (len(ta) + len(tb))


def unescape_latex(text: str) -> str:
    """Invert :func:`src.data.resume.escape_latex` on a LaTeX fragment.

    Args:
        text: LaTeX fragment as rendered by the project template.

    Returns:
        str: Plain text.
    """
    replacements = (
        (r"\textbackslash{}", "\\"),
        (r"\textasciitilde{}", "~"),
        (r"\textasciicircum{}", "^"),
        (r"\&", "&"),
        (r"\%", "%"),
        (r"\$", "$"),
        (r"\#", "#"),
        (r"\_", "_"),
        (r"\{", "{"),
        (r"\}", "}"),
        ("---", "—"),
        ("--", "–"),
    )
    for old, new in replacements:
        text = text.replace(old, new)
    return re.sub(r"\s+", " ", text).strip()


def select_relevant_coursework(
    coursework: list[str],
    job: Any,
    max_courses: int = 3,
) -> list[str]:
    """Select and rank coursework by keyword overlap with the target job posting.

    Deterministic, allowlist-only filter: prioritizes courses that map to at least
    one job keyword, technology, or title/description token.

    Args:
        coursework: Candidate's verified completed coursework list.
        job: Target JobPosting.
        max_courses: Maximum number of courses to keep for single-page budget.

    Returns:
        list[str]: Ranked, relevant courses (up to max_courses).
    """
    if not coursework:
        return []

    # Build job text and tokens
    job_title = getattr(job, "title", "") or ""
    job_desc = getattr(job, "raw_description", "") or ""
    job_techs = getattr(job, "technologies", []) or []
    job_keywords = getattr(job, "keywords", []) or []
    job_resps = getattr(job, "responsibilities", []) or []
    job_reqs = getattr(job, "requirements", []) or []

    job_text = " ".join(
        [
            job_title,
            job_desc,
            " ".join(job_techs),
            " ".join(job_keywords),
            " ".join(job_resps),
            " ".join(job_reqs),
        ]
    )

    # Generic filler tokens that appear ubiquitously and cause false overlap
    generic_course_tokens = {
        "develop", "development", "engin", "engineering", "introduct", "introduction",
        "basic", "fundamental", "principle", "project", "advanc", "advanced", "concept",
        "comput", "computing", "scienc", "science", "technolog", "technology", "lab",
        "laboratori", "laboratorio", "cours", "course", "disciplin", "disciplina", "intern",
    }

    job_tokens = (set(tokenize(job_text)) - STOPWORDS) - generic_course_tokens
    job_text_lower = job_text.lower()

    # Domain vocabulary markers
    embedded_domain = {
        "embed", "mcu", "microcontrol", "firmwar", "hardwar", "rtos", "circuit",
        "signal", "architectur", "dsp", "ecu", "automotiv", "can", "spi", "i2c", "tinyml",
        "freertos", "arm", "cortex",
    }
    ai_domain = {
        "ai", "ml", "learn", "neural", "deep", "data", "vision", "nlp", "model", "python",
    }
    backend_domain = {
        "backend", "distribut", "system", "databas", "sql", "api", "cloud", "network", "server",
    }

    # Common course-to-technology semantic phrase bridges
    phrase_bridges: list[tuple[str, set[str]]] = [
        ("operating system", {"rto", "rtos", "freerto", "freertos", "os", "kernel"}),
        ("real-time", {"rto", "rtos", "freerto", "freertos", "embed", "embedded"}),
        ("real time", {"rto", "rtos", "freerto", "freertos", "embed", "embedded"}),
        ("signal process", {"dsp", "signal", "filter"}),
        ("microcontrol", {"mcu", "embed", "embedded", "firmwar", "arm"}),
        ("cloud", {"distribut", "distributed", "backend", "aws", "docker"}),
        ("databas", {"sql", "relat", "relational", "postgre", "postgres"}),
    ]

    scored: list[tuple[float, int, str]] = []
    for idx, course in enumerate(coursework):
        raw_course_tokens = set(tokenize(course))
        c_tokens = (raw_course_tokens - STOPWORDS) - generic_course_tokens
        if not c_tokens:
            continue

        course_lower = course.lower()
        expanded_c_tokens = set(c_tokens)
        for phrase, added_tokens in phrase_bridges:
            if phrase in course_lower:
                expanded_c_tokens.update(added_tokens)

        # Direct overlap with job tokens
        direct_matches = expanded_c_tokens & job_tokens
        score = float(len(direct_matches) * 2.0)

        # Domain overlap boost
        if (job_tokens & embedded_domain) and (expanded_c_tokens & embedded_domain):
            score += 3.0
        if (job_tokens & ai_domain) and (expanded_c_tokens & ai_domain):
            score += 3.0
        if (job_tokens & backend_domain) and (expanded_c_tokens & backend_domain):
            score += 3.0

        if score > 0:
            scored.append((score, idx, course))

    scored.sort(key=lambda x: (-x[0], x[1]))
    selected = [course for _, _, course in scored[:max_courses]]

    return selected if selected else coursework[:max_courses]
