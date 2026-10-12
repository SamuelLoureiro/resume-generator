"""List Google Gemini models available to the configured API key.

Performs a single API call to fetch available models and checks whether
the project-configured model identifiers (generation, judge, override, embedding)
exist in the returned catalog.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path so src imports work cleanly
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.config import ALLOWED_GENERATION_MODELS, get_settings


def normalize(name: str) -> str:
    """Normalize model identifier for comparison by stripping 'models/' and lowercase."""
    cleaned = name.strip()
    if cleaned.startswith("models/"):
        cleaned = cleaned[len("models/") :]
    return cleaned.lower()


def fetch_models(api_key: str) -> list[dict[str, str]]:
    """Fetch available models using Google GenAI SDK (or google.generativeai fallback)."""
    models_info: list[dict[str, str]] = []

    try:
        from google import genai

        client = genai.Client(api_key=api_key)
        for model in client.models.list():
            name = getattr(model, "name", "")
            display_name = getattr(model, "display_name", "") or ""
            desc = getattr(model, "description", "") or ""
            actions = getattr(model, "supported_actions", None) or []
            models_info.append(
                {
                    "name": name,
                    "display_name": display_name,
                    "description": desc[:80] + ("..." if len(desc) > 80 else ""),
                    "actions": ", ".join(actions) if isinstance(actions, list) else str(actions),
                }
            )
        return models_info
    except Exception as e_genai:
        # Fallback to google.generativeai if google.genai has issues
        try:
            import google.generativeai as legacy_genai

            legacy_genai.configure(api_key=api_key)
            for model in legacy_genai.list_models():
                name = getattr(model, "name", "")
                display_name = getattr(model, "display_name", "") or ""
                desc = getattr(model, "description", "") or ""
                methods = getattr(model, "supported_generation_methods", None) or []
                models_info.append(
                    {
                        "name": name,
                        "display_name": display_name,
                        "description": desc[:80] + ("..." if len(desc) > 80 else ""),
                        "actions": ", ".join(methods) if isinstance(methods, list) else str(methods),
                    }
                )
            return models_info
        except Exception as e_legacy:
            raise RuntimeError(
                f"Failed to query Gemini API via google.genai ({e_genai}) and google.generativeai ({e_legacy})"
            ) from e_legacy


def main() -> None:
    """Execute model listing and verify configured IDs."""
    settings = get_settings()

    if not settings.google_api_key:
        print("ERROR: GOOGLE_API_KEY is not set in environment or .env file.", file=sys.stderr)
        sys.exit(1)

    print("Fetching available models from Google Gemini API (single API call)...")
    try:
        available_models = fetch_models(settings.google_api_key)
    except Exception as err:
        print(f"ERROR: Could not list models: {err}", file=sys.stderr)
        sys.exit(1)

    print(f"\nRetrieved {len(available_models)} models from API.\n")
    print(f"{'API Model Name':<45} | {'Display Name':<35}")
    print("-" * 83)
    for m in sorted(available_models, key=lambda x: x["name"]):
        print(f"{m['name']:<45} | {m['display_name']:<35}")

    # Map of normalized name -> raw model info
    available_map: dict[str, dict[str, str]] = {}
    for m in available_models:
        available_map[normalize(m["name"])] = m

    # Configured IDs to check
    checks = [
        ("GENERATION_MODEL (default)", settings.generation_model),
        ("JUDGE_MODEL (default)", settings.judge_model),
        ("GENERATION_OVERRIDE (production)", "gemini-3.8-flash"),
        ("EMBEDDING_MODEL", settings.gemini_embedding_model),
    ]

    print("\n" + "=" * 83)
    print("VERIFICATION OF CONFIGURED MODEL IDENTIFIERS")
    print("=" * 83)

    missing: list[tuple[str, str]] = []
    for label, model_id in checks:
        norm = normalize(model_id)
        if norm in available_map:
            canonical = available_map[norm]["name"]
            print(f"[FOUND]     {label:<35} -> '{model_id}' (matches '{canonical}')")
        else:
            print(f"[NOT FOUND] {label:<35} -> '{model_id}'")
            missing.append((label, model_id))

    print("-" * 83)
    if missing:
        print("\nWARNING: Some configured model IDs were NOT found in the API catalog!")
        for label, model_id in missing:
            print(f"  - {label}: {model_id}")
        print("\nPlease review the available API models listed above.")
    else:
        print("\nSUCCESS: All configured model IDs exist and are available to your key.")


if __name__ == "__main__":
    main()
