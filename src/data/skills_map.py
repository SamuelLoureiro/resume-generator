"""Deterministic category mapping for candidate and technical skills.

Ensures technical skills (e.g. ROS 2, FreeRTOS, PyTorch) are strictly categorized
according to deterministic domain taxonomy rather than nondeterministic LLM grouping.
"""

from __future__ import annotations

import re
from typing import Any

from src.data.resume import ResumeSkillCategory

# Canonical domain categories by language
CATEGORY_NAMES: dict[str, dict[str, str]] = {
    "en": {
        "prog": "Programming Languages",
        "embedded": "Embedded Systems & Communication",
        "robotics": "Robotics & Middleware",
        "frameworks": "Frameworks and Libraries",
        "databases": "Databases",
        "tools": "Tools and Platforms",
        "soft": "Interpersonal Skills",
    },
    "pt": {
        "prog": "Linguagens de Programação",
        "embedded": "Sistemas Embarcados & Comunicação",
        "robotics": "Robótica & Middleware",
        "frameworks": "Frameworks e Bibliotecas",
        "databases": "Bancos de Dados",
        "tools": "Ferramentas e Plataformas",
        "soft": "Competências Interpessoais",
    },
    "fr": {
        "prog": "Langages de programmation",
        "embedded": "Systèmes embarqués & Communication",
        "robotics": "Robotique & Middleware",
        "frameworks": "Frameworks et bibliothèques",
        "databases": "Bases de données",
        "tools": "Outils et plateformes",
        "soft": "Compétences relationnelles",
    },
}

# Preferred presentation order of categories in resumes
CATEGORY_ORDER = ["prog", "embedded", "robotics", "frameworks", "databases", "tools", "soft"]

# Deterministic mapping from normalized skill tokens to category key
SKILL_TO_CATEGORY_KEY: dict[str, str] = {
    # 1. Programming Languages
    "python": "prog",
    "c": "prog",
    "c++": "prog",
    "c / c++": "prog",
    "c/c++": "prog",
    "java": "prog",
    "dart": "prog",
    "javascript": "prog",
    "typescript": "prog",
    "sql": "prog",
    "rust": "prog",
    "go": "prog",
    "html/css": "prog",

    # 2. Embedded Systems, Hardware & Bus Protocols
    "freertos": "embedded",
    "can bus": "embedded",
    "can": "embedded",
    "can bus / i2c / spi": "embedded",
    "spi": "embedded",
    "i2c": "embedded",
    "uart": "embedded",
    "pio": "embedded",
    "spi / uart / i2c / pio": "embedded",
    "easyeda": "embedded",
    "raspberry pi pico (rp2350)": "embedded",
    "raspberry pi pico": "embedded",
    "raspberry pi": "embedded",
    "stm32 nucleo": "embedded",
    "stm32": "embedded",
    "arduino": "embedded",
    "tinyml": "embedded",
    "edge impulse": "embedded",
    "pcb design": "embedded",

    # 3. Robotics & Middleware (ROS 2 MUST be here)
    "ros 2": "robotics",
    "ros2": "robotics",
    "ros": "robotics",
    "robot operating system": "robotics",
    "micro-ros": "robotics",
    "microros": "robotics",
    "gazebo": "robotics",
    "dds": "robotics",

    # 4. Frameworks & Machine Learning
    "pytorch": "frameworks",
    "tensorflow": "frameworks",
    "scikit-learn": "frameworks",
    "scikitlearn": "frameworks",
    "pandas": "frameworks",
    "numpy": "frameworks",
    "opencv": "frameworks",
    "llamaindex": "frameworks",
    "langchain": "frameworks",
    "flutter": "frameworks",
    "flutter / dart": "frameworks",
    "qt": "frameworks",
    "fastapi": "frameworks",
    "django": "frameworks",
    "flask": "frameworks",
    "machine learning": "frameworks",
    "deep learning": "frameworks",

    # 5. Databases
    "mongodb": "databases",
    "postgresql": "databases",
    "sqlite": "databases",
    "chromadb": "databases",
    "redis": "databases",
    "mysql": "databases",

    # 6. Tools, Platforms & DevOps
    "git": "tools",
    "github": "tools",
    "git / github": "tools",
    "docker": "tools",
    "cmake": "tools",
    "android studio": "tools",
    "linux": "tools",
    "llms": "tools",
    "power bi": "tools",
    "rest apis": "tools",
    "postman": "tools",

    # 7. Soft Skills
    "team management": "soft",
    "cross-functional collaboration": "soft",
    "problem solving": "soft",
    "project management": "soft",
}


def normalize_skill_token(skill: str) -> str:
    """Normalize a skill string for lookup in the category mapping."""
    return skill.strip().lower()


def get_skill_category_key(skill: str) -> str | None:
    """Return the canonical category key ('prog', 'embedded', 'robotics', etc.) for a skill.

    Args:
        skill: Raw skill name (e.g. 'ROS 2', 'PyTorch').

    Returns:
        str | None: Category key, or None if the skill is unmapped.
    """
    tok = normalize_skill_token(skill)
    if tok in SKILL_TO_CATEGORY_KEY:
        return SKILL_TO_CATEGORY_KEY[tok]

    # Try matching without whitespace, dashes or slashes
    squashed = re.sub(r"[\s\-_/]+", "", tok)
    for k, v in SKILL_TO_CATEGORY_KEY.items():
        if re.sub(r"[\s\-_/]+", "", k) == squashed:
            return v
    return None


def get_skill_category_name(skill: str, language: str = "en") -> str | None:
    """Return the localized category heading for a skill.

    Args:
        skill: Raw skill name.
        language: Language code ('en', 'pt', 'fr').

    Returns:
        str | None: Localized category name, or None if unmapped.
    """
    key = get_skill_category_key(skill)
    if key is None:
        return None
    names = CATEGORY_NAMES.get(language, CATEGORY_NAMES["en"])
    return names.get(key)


def flag_unknown_skills(skills: list[str]) -> list[str]:
    """Identify skills that do not have a defined category in the taxonomy.

    Args:
        skills: List of skill strings.

    Returns:
        list[str]: Skills not found in the deterministic mapping.
    """
    return [s for s in skills if get_skill_category_key(s) is None]


def reorganize_resume_skills(
    categories: list[ResumeSkillCategory] | list[dict[str, Any]],
    language: str = "en",
) -> list[ResumeSkillCategory]:
    """Deterministically reorganize skills into canonical categories.

    Moves skills such as 'ROS 2' to Robotics & Middleware and prevents LLM miscategorization.

    Args:
        categories: Input list of ResumeSkillCategory objects or dictionaries.
        language: Target document language ('en', 'pt', 'fr').

    Returns:
        list[ResumeSkillCategory]: Clean, canonical list of categorized skills.
    """
    names = CATEGORY_NAMES.get(language, CATEGORY_NAMES["en"])
    buckets: dict[str, list[str]] = {k: [] for k in CATEGORY_ORDER}
    unknown_bucket: list[str] = []

    # Flatten skills while preserving first-seen capitalization and order
    seen: set[str] = set()
    for cat in categories:
        if isinstance(cat, dict):
            raw_skills = cat.get("skills", [])
        else:
            raw_skills = getattr(cat, "skills", [])

        for s in raw_skills:
            clean_s = str(s).strip()
            if not clean_s or clean_s.lower() in seen:
                continue
            seen.add(clean_s.lower())

            cat_key = get_skill_category_key(clean_s)
            if cat_key and cat_key in buckets:
                buckets[cat_key].append(clean_s)
            else:
                unknown_bucket.append(clean_s)

    # If unknown skills exist, append them to Tools & Platforms
    if unknown_bucket:
        buckets["tools"].extend(unknown_bucket)

    # Build ordered output categories (omitting empty buckets)
    result: list[ResumeSkillCategory] = []
    for key in CATEGORY_ORDER:
        skills_in_bucket = buckets[key]
        if skills_in_bucket:
            cat_name = names[key]
            result.append(
                ResumeSkillCategory(
                    category_name=cat_name,
                    skills=skills_in_bucket,
                )
            )

    return result
