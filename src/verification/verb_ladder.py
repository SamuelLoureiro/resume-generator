"""Verb ladder used by the inflation check (M2).

PROPOSED by the agent, pending human approval (research plan, section 5).
Levels mirror :data:`src.data.facts.SCOPE_LEVEL_NAMES`:
1 participated, 2 contributed, 3 developed, 4 led.

Design-type verbs (*designed*, *architected*, *engineered*) are level 3 **only if**
the matched fact really describes design work; the evidence test lives in
:func:`design_evidence_in`. Entries for French and Portuguese are a starter set and
should be extended as real FR/PT postings enter the benchmark.
"""

from __future__ import annotations

import re
from typing import NamedTuple

# phrase (lowercase) -> level. Multi-word phrases are matched longest-first.
VERB_LEVELS: dict[str, int] = {
    # --- Level 1: participated ------------------------------------------------
    "participated in": 1, "participated": 1, "took part in": 1, "assisted in": 1,
    "assisted with": 1, "assisted": 1, "supported": 1, "worked on": 1,
    "involved in": 1, "exposed to": 1,
    "participou de": 1, "participou em": 1, "auxiliou": 1, "apoiou": 1,
    "participé à": 1, "participé au": 1, "assisté": 1, "soutenu": 1,
    # --- Level 2: contributed -------------------------------------------------
    "contributed to": 2, "contributed": 2, "co-designed": 2, "co-developed": 2,
    "helped build": 2, "helped develop": 2, "helped design": 2, "helped implement": 2,
    "collaborated on": 2, "collaborated with": 2, "co-built": 2,
    "contribuiu para": 2, "contribuiu com": 2, "colaborou em": 2,
    "contribué à": 2, "contribué au": 2, "collaboré à": 2,
    # --- Level 3: developed ---------------------------------------------------
    "developed": 3, "built": 3, "implemented": 3, "integrated": 3, "trained": 3,
    "wrote": 3, "created": 3, "delivered": 3, "deployed": 3, "automated": 3,
    "configured": 3, "established": 3, "structured": 3, "tested": 3, "optimized": 3,
    "programmed": 3, "coded": 3, "organized": 3, "analyzed": 3, "migrated": 3,
    "refactored": 3, "evaluated": 3, "set up": 3, "produced": 3, "applied": 3,
    "desenvolveu": 3, "construiu": 3, "implementou": 3, "integrou": 3, "treinou": 3,
    "criou": 3, "entregou": 3, "automatizou": 3, "configurou": 3, "organizou": 3,
    "développé": 3, "construit": 3, "implémenté": 3, "intégré": 3, "entraîné": 3,
    "créé": 3, "livré": 3, "automatisé": 3, "configuré": 3, "organisé": 3,
    # --- Level 4: led ---------------------------------------------------------
    "led": 4, "managed": 4, "owned": 4, "founded": 4, "directed": 4, "coordinated": 4,
    "spearheaded": 4, "headed": 4, "supervised": 4, "oversaw": 4, "mentored": 4,
    "liderou": 4, "gerenciou": 4, "coordenou": 4, "dirigiu": 4, "fundou": 4,
    "supervisionou": 4,
    "dirigé": 4, "géré": 4, "coordonné": 4, "piloté": 4, "fondé": 4, "encadré": 4,
}

# Verbs that imply design work: level 3 only when the source fact describes design.
DESIGN_VERBS: dict[str, int] = {
    "designed": 3, "architected": 3, "engineered": 3,
    "projetou": 3, "arquitetou": 3,
    "conçu": 3, "architecturé": 3,
}

# Stems that count as "the fact really describes design".
DESIGN_EVIDENCE_STEMS: tuple[str, ...] = (
    "design", "architect", "engineer", "projet", "concep", "conç",
)

_ALL_PHRASES: dict[str, int] = {**VERB_LEVELS, **DESIGN_VERBS}
_MAX_PHRASE_WORDS = max(len(p.split()) for p in _ALL_PHRASES)
_WORD_RE = re.compile(r"[\w'’+\-]+", re.UNICODE)


class LeadVerb(NamedTuple):
    """Lead verb of a bullet and its scope level.

    Attributes:
        phrase: Matched ladder phrase (lowercase), e.g. ``"participated in"``.
        level: Scope level 1-4.
        is_design: True when the verb is a design-type verb (conditional level 3).
    """

    phrase: str
    level: int
    is_design: bool


def extract_lead_verb(bullet: str) -> LeadVerb | None:
    """Find the lead verb of a bullet in the ladder.

    Leading adverbs ending in ``-ly`` ("Successfully delivered ...") are skipped.
    Only the lead verb is assessed; later verbs in the sentence are not (documented
    limitation of M2).

    Args:
        bullet: Bullet text.

    Returns:
        LeadVerb | None: Match, or None if the lead word is not on the ladder.
    """
    words = [w.lower() for w in _WORD_RE.findall(bullet or "")]
    while len(words) > 1 and words[0].endswith("ly"):
        words = words[1:]
    for size in range(min(_MAX_PHRASE_WORDS, len(words)), 0, -1):
        phrase = " ".join(words[:size])
        if phrase in _ALL_PHRASES:
            return LeadVerb(phrase, _ALL_PHRASES[phrase], phrase in DESIGN_VERBS)
    return None


def verb_words(text: str) -> set[str]:
    """Return the set of lowercase words of ``text`` (used to see which verbs a fact uses)."""
    return {w.lower() for w in _WORD_RE.findall(text or "")}


def design_evidence_in(text: str) -> bool:
    """Return True if ``text`` describes design/architecture/engineering work."""
    lowered = (text or "").lower()
    return any(stem in lowered for stem in DESIGN_EVIDENCE_STEMS)
