"""Ground-truth lookups derived from the candidate profile and verified atomic facts."""

from __future__ import annotations

import re
from typing import Any, Iterable

from src.data.candidate import CandidateProfile
from src.data.facts import CandidateFacts
from src.verification.text_utils import ngram_keys, term_key, term_keys

_NUMBER_RE = re.compile(r"(?<![\w.,/])(\d+(?:[.,]\d+)*)(\+|%)?(?![\w/])")
_YEAR_RE = re.compile(r"(?<!\d)(\d{4})(?!\d)")
_CONTACT_FIELDS = {"email", "phone", "linkedin_url", "github_url", "portfolio_url"}


def extract_numbers(text: str) -> list[str]:
    """Extract numeric claims (``80%``, ``5+``, ``50,000``, ``2``) from text.

    Digits glued to letters (``RP2350``, ``I2C``) and date fragments (``09/2025``) are
    not numeric claims and are skipped.

    Args:
        text: Free text.

    Returns:
        list[str]: Numeric tokens with their ``%``/``+`` suffix, commas removed.
    """
    return [
        match.group(1).replace(",", "") + (match.group(2) or "")
        for match in _NUMBER_RE.finditer(text or "")
    ]


def _walk_strings(value: Any, skip_keys: set[str] | None = None) -> Iterable[str]:
    """Yield every string inside nested dicts/lists, optionally skipping some dict keys."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, inner in value.items():
            if skip_keys and key in skip_keys:
                continue
            yield from _walk_strings(inner, skip_keys)
    elif isinstance(value, (list, tuple)):
        for inner in value:
            yield from _walk_strings(inner, skip_keys)


class GroundTruth:
    """Lookup tables of everything the candidate is allowed to claim.

    Contact fields (phone, email, links) are deliberately excluded from the corpus so
    their digits can never "support" a numeric claim.

    Attributes:
        profile: Candidate profile (source of truth for organizations, titles, dates).
        facts: Verified atomic facts (source of truth for scope, metrics and tags).
        skill_keys: Allowlist of term keys (profile skills, technologies, fact tags).
        number_tokens: Numeric tokens present anywhere in profile text or facts.
    """

    def __init__(self, profile: CandidateProfile, facts: CandidateFacts) -> None:
        """Build the allowlists.

        Args:
            profile: Candidate profile.
            facts: Verified atomic facts.
        """
        self.profile = profile
        self.facts = facts
        self.skill_keys: set[str] = self._build_skill_keys()
        self.number_tokens: set[str] = self._build_number_tokens()
        self._text_keys: set[str] = self._build_text_keys()

    def _build_skill_keys(self) -> set[str]:
        skills = self.profile.skills
        items: list[str] = [
            *skills.programming_languages,
            *skills.frameworks_and_libraries,
            *skills.databases,
            *skills.tools_and_platforms,
            *skills.soft_skills,
        ]
        for exp in self.profile.experiences:
            items.extend(exp.technologies)
        for proj in self.profile.projects:
            items.extend(proj.technologies)
        for fact in self.facts.facts:
            items.extend(fact.tags)
        return term_keys(items)

    def _verified_texts(self) -> list[str]:
        """All verified free text (profile minus contact fields, fact texts and metrics)."""
        texts = list(
            _walk_strings(
                self.profile.model_dump(exclude={"contact": _CONTACT_FIELDS}),
                skip_keys=_CONTACT_FIELDS,
            )
        )
        for fact in self.facts.facts:
            texts.append(fact.text)
            texts.extend(fact.metrics)
        return texts

    def _build_number_tokens(self) -> set[str]:
        tokens: set[str] = set()
        for text in self._verified_texts():
            tokens.update(extract_numbers(text))
            tokens.update(_YEAR_RE.findall(text))
        return tokens

    def _build_text_keys(self) -> set[str]:
        keys: set[str] = set()
        for text in self._verified_texts():
            keys |= ngram_keys(text, max_n=3)
        return keys

    def has_term(self, term: str) -> bool:
        """Return True if the candidate verifiably has ``term``.

        True if the term is on the skill allowlist or appears (as a 1-3 word phrase)
        anywhere in the verified profile or fact text. Broader than
        :meth:`is_allowed_skill` on purpose: it decides which job keywords the
        candidate can honestly echo, not what may appear in a skills list.

        Args:
            term: Job keyword.

        Returns:
            bool: Whether the term is supported. Empty terms are never supported.
        """
        key = term_key(term)
        if not key:
            return False
        return key in self.skill_keys or key in self._text_keys

    def is_allowed_skill(self, item: str) -> bool:
        """Return True if every atomic term of ``item`` is on the allowlist.

        Args:
            item: Skill or technology string (may be composite, e.g. ``"C / C++"``).

        Returns:
            bool: False if any atomic term is unknown; True for an empty item.
        """
        keys = term_keys([item])
        return all(key in self.skill_keys for key in keys)

    def is_supported_number(self, token: str, extra_allowed: set[str] | None = None) -> bool:
        """Return True if a numeric token is backed by the profile/facts.

        A token with a ``%``/``+`` suffix must appear with that exact suffix. A bare
        number is supported if the same number appears with any suffix (writing "5"
        when the truth is "5+" is not an overstatement).

        Args:
            token: Token from :func:`extract_numbers`.
            extra_allowed: Additional allowed tokens (e.g. numbers in the job title).

        Returns:
            bool: Whether the number is supported.
        """
        allowed = self.number_tokens | (extra_allowed or set())
        if token in allowed:
            return True
        core = token.rstrip("+%")
        if core == token:  # bare number: any suffix variant is fine
            return any(a.rstrip("+%") == core for a in allowed)
        return False
