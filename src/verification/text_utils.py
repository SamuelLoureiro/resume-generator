"""Deterministic text normalisation helpers shared by all verification checks.

Everything here is pure string processing: no network, no LLM, no randomness.
"""

from __future__ import annotations

import re
from typing import Iterable

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
