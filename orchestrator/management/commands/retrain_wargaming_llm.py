"""
Build a unified Ollama model for wargaming analysis from geography, personnel,
and weapons data.

This command does not fine-tune model weights. Instead, it creates an Ollama
model with a strong system prompt plus a structured knowledge compendium built
from the full dataset so the model can reason from far more than a few short
summaries.
"""
import os
import subprocess
import tempfile
from typing import Any, Dict, Iterable, List

import requests
from django.core.management.base import BaseCommand, CommandError

from orchestrator.services import config_provider
from war_game.project_config import UNIFIED_LLM_TRAINING_CONFIG


DEFAULT_TRAINING_SYSTEM_PROMPT = """You are a wargaming analyst specializing in Middle East conflict scenarios.

Language:
- The knowledge reference below is written in English, but you MUST always respond in fluent, natural Persian (Farsi) unless the user explicitly writes in English.
- Write in clear, formal, native-quality Persian suitable for military analysis. Do NOT mix English words into Persian sentences, except for standard proper nouns and equipment names (e.g. F-16, S-300), which you may keep in their common form.
- Translate all analysis, reasoning, and factual descriptions into Persian.

Your job:
- Understand and use the full structured knowledge reference below.
- Answer with grounded military reasoning that combines geography, personnel, and weapons.
- Compare countries side by side when asked.
- Explain who has an advantage, why, and under what assumptions.
- Give practical strategic advice when asked, but stay high-level and evidence-based.

Rules:
- Use the knowledge reference and runtime context provided by the application.
- Prefer specific facts, named regions, units, quantities, and equipment when available.
- If the data is incomplete, say what is missing instead of inventing details.
- Be concise but substantive. Default to clear paragraphs or compact bullets."""


def _clean_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    return " ".join(str(value).split())


def _compact_list(values: Iterable[Any], limit: int | None = None) -> str:
    cleaned = [_clean_text(value) for value in values if _clean_text(value)]
    if limit is not None:
        cleaned = cleaned[:limit]
    return ", ".join(cleaned)


def _truncate_block(title: str, text: str, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit("\n", 1)[0].rstrip()
    return f"{clipped}\n[{title} truncated to fit context budget]"


def _build_geography_knowledge(data: Dict[str, Any]) -> str:
    regions = data.get("regions", {}) or {}
    lines = ["GEOGRAPHY KNOWLEDGE", "Regional operational picture:"]

    for key, region in regions.items():
        name = region.get("name", key.replace("_", " ").title())
        terrain = _clean_text((region.get("terrain") or {}).get("description"))
        climate = _clean_text((region.get("weather") or {}).get("climate"))
        urban = _compact_list((region.get("strategic_features") or {}).get("urban_centers", []), limit=6)
        chokepoints = _compact_list((region.get("strategic_features") or {}).get("chokepoints", []), limit=6)
        resources = _compact_list((region.get("strategic_features") or {}).get("resources", []), limit=6)
        defensive = _compact_list(
            (region.get("military_considerations") or {}).get("defensive_positions", []),
            limit=6,
        )
        offensive = _compact_list(
            (region.get("military_considerations") or {}).get("offensive_routes", []),
            limit=6,
        )
        advantages = _compact_list(
            (region.get("military_considerations") or {}).get("terrain_advantages", []),
            limit=6,
        )
        disadvantages = _compact_list(
            (region.get("military_considerations") or {}).get("terrain_disadvantages", []),
            limit=6,
        )
        lines.append(
            f"- {name}: terrain={terrain}; climate={climate}; urban_centers={urban}; "
            f"chokepoints={chokepoints}; resources={resources}; defensive_positions={defensive}; "
            f"offensive_routes={offensive}; terrain_advantages={advantages}; "
            f"terrain_disadvantages={disadvantages}."
        )

    weather_patterns = data.get("weather_patterns", {}) or {}
    if weather_patterns:
        lines.append("Regional weather patterns:")
        for name, details in weather_patterns.items():
            lines.append(f"- {name.replace('_', ' ').title()}: {_clean_text(details)}")

    chokepoints = data.get("strategic_chokepoints", {}) or {}
    if chokepoints:
        lines.append("Strategic chokepoints:")
        for name, details in chokepoints.items():
            if isinstance(details, dict):
                description = _clean_text(details.get("description"))
                importance = _clean_text(details.get("importance"))
                lines.append(
                    f"- {name.replace('_', ' ').title()}: description={description}; importance={importance}"
                )
            else:
                lines.append(f"- {name.replace('_', ' ').title()}: {_clean_text(details)}")

    infrastructure = data.get("infrastructure", {}) or {}
    if infrastructure:
        lines.append("Infrastructure factors:")
        for name, details in infrastructure.items():
            lines.append(f"- {name.replace('_', ' ').title()}: {_clean_text(details)}")

    return "\n".join(lines)


def _build_personnel_knowledge(data: Dict[str, Any]) -> str:
    countries = ((data.get("personnel_data") or {}).get("countries")) or {}
    lines = ["PERSONNEL KNOWLEDGE", "Country force structure and manpower:"]

    for key, country in countries.items():
        name = country.get("name", key.replace("_", " ").title())
        total = _clean_text(country.get("total_personnel", "N/A"))
        active = _clean_text(country.get("active_duty", "N/A"))
        reserves = _clean_text(country.get("reserves", "N/A"))
        branch_bits: List[str] = []

        for branch_name, branch in (country.get("branches") or {}).items():
            branch_label = branch_name.replace("_", " ").title()
            special_units = []
            for unit_name, unit in (branch.get("special_units") or {}).items():
                quantity = _clean_text((unit or {}).get("quantity", "unknown"))
                description = _clean_text((unit or {}).get("description", ""))
                special_units.append(f"{unit_name.replace('_', ' ')} ({quantity}; {description})")
            branch_bits.append(
                f"{branch_label}: special_units={_compact_list(special_units, limit=8) or 'none listed'}"
            )

        lines.append(
            f"- {name}: total_personnel={total}; active_duty={active}; reserves={reserves}; "
            f"branches={' | '.join(branch_bits) if branch_bits else 'not provided'}."
        )

    branch_characteristics = data.get("branch_characteristics", {}) or {}
    if branch_characteristics:
        lines.append("Branch characteristics:")
        for branch_name, details in branch_characteristics.items():
            lines.append(f"- {branch_name.replace('_', ' ').title()}: {_clean_text(details)}")

    rank_hierarchy = data.get("rank_hierarchy", {}) or {}
    if rank_hierarchy:
        lines.append("Rank hierarchy:")
        for branch_name, details in rank_hierarchy.items():
            if isinstance(details, list):
                lines.append(
                    f"- {branch_name.replace('_', ' ').title()}: {_compact_list(details, limit=20)}"
                )
            else:
                lines.append(f"- {branch_name.replace('_', ' ').title()}: {_clean_text(details)}")

    return "\n".join(lines)


def _build_weapons_knowledge(data: Dict[str, Any]) -> str:
    categories = data.get("weapon_categories", {}) or {}
    lines = ["WEAPONS KNOWLEDGE", "Weapon categories, capabilities, and national holdings:"]
    country_holdings: Dict[str, List[str]] = {}

    for key, category in categories.items():
        category_name = category.get("name", key.replace("_", " ").title())
        category_description = _clean_text(category.get("description"))
        lines.append(f"- Category {category_name}: {category_description}")

        for type_name, weapon_type in (category.get("types") or {}).items():
            label = weapon_type.get("name", type_name.replace("_", " ").title())
            description = _clean_text(weapon_type.get("description"))
            effectiveness = _clean_text(weapon_type.get("effectiveness"))
            range_value = _clean_text(weapon_type.get("range"))
            accuracy = _clean_text(weapon_type.get("accuracy"))
            mobility = _clean_text(weapon_type.get("mobility"))
            logistics = _clean_text(weapon_type.get("logistics"))
            cost = _clean_text(weapon_type.get("cost"))
            models = _compact_list(weapon_type.get("models", []), limit=8)
            lines.append(
                f"  - {label}: description={description}; effectiveness={effectiveness}; "
                f"range={range_value}; accuracy={accuracy}; mobility={mobility}; "
                f"logistics={logistics}; cost={cost}; representative_models={models or 'not listed'}."
            )

            for country_key, country_data in (weapon_type.get("countries") or {}).items():
                country_name = country_key.replace("_", " ").title()
                quantity = _clean_text((country_data or {}).get("quantity", "unknown"))
                primary_models = _compact_list(
                    (country_data or {}).get("primary_models", []) or (country_data or {}).get("models", []),
                    limit=6,
                )
                country_holdings.setdefault(country_name, []).append(
                    f"{label} qty={quantity} models={primary_models or 'not listed'}"
                )

    if country_holdings:
        lines.append("Country holdings overview:")
        for country_name in sorted(country_holdings):
            lines.append(f"- {country_name}: {'; '.join(country_holdings[country_name])}")

    return "\n".join(lines)


def _build_full_knowledge_base(
    geo_data: Dict[str, Any],
    pers_data: Dict[str, Any],
    wep_data: Dict[str, Any],
    max_total_chars: int,
) -> str:
    section_budget = max(max_total_chars // 3, 4000)
    sections = [
        _truncate_block("Geography knowledge", _build_geography_knowledge(geo_data), section_budget),
        _truncate_block("Personnel knowledge", _build_personnel_knowledge(pers_data), section_budget),
        _truncate_block("Weapons knowledge", _build_weapons_knowledge(wep_data), section_budget),
    ]
    knowledge = "\n\n".join(sections)
    return _truncate_block("Unified knowledge base", knowledge, max_total_chars)


class Command(BaseCommand):
    help = "Create a unified Ollama wargaming model using the full structured dataset."

    def add_arguments(self, parser):
        parser.add_argument(
            "--model",
            type=str,
            default=None,
            help="Base Ollama model (defaults to the admin LLM Config base model).",
        )
        parser.add_argument(
            "--base-url",
            type=str,
            default=None,
            help="Ollama base URL (defaults to the admin LLM Config).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Recreate model even if it already exists",
        )
        parser.add_argument(
            "--max-knowledge-chars",
            type=int,
            default=UNIFIED_LLM_TRAINING_CONFIG["max_knowledge_chars"],
            help="Maximum characters to embed in the model knowledge compendium",
        )
        parser.add_argument(
            "--num-ctx",
            type=int,
            default=None,
            help="Context window to configure on the trained model (defaults to admin LLM Config).",
        )

    def handle(self, *args, **options):
        defaults = config_provider.get_training_defaults()
        base_model = options["model"] or defaults["default_base_model"]
        base_url = options["base_url"] or defaults["base_url"]
        force = options["force"]
        max_knowledge_chars = options["max_knowledge_chars"]
        num_ctx = options["num_ctx"] or defaults["num_ctx"]

        self.stdout.write(self.style.SUCCESS("Starting unified wargaming LLM training..."))

        try:
            r = requests.get(
                f"{base_url}/api/tags",
                timeout=UNIFIED_LLM_TRAINING_CONFIG["ollama_healthcheck_timeout_seconds"],
            )
            if r.status_code != 200:
                raise CommandError(f"Ollama not responding at {base_url}")
        except requests.exceptions.ConnectionError:
            raise CommandError(f"Cannot connect to Ollama at {base_url}. Start Ollama first.")

        models = [m.get("name") for m in r.json().get("models", [])]
        custom_model_name = UNIFIED_LLM_TRAINING_CONFIG["custom_model_name"]
        if custom_model_name in models and not force:
            self.stdout.write(
                self.style.WARNING(
                    f"Model {custom_model_name} already exists. Use --force to recreate."
                )
            )
            return

        geo_data = config_provider.get_knowledge("geography")
        pers_data = config_provider.get_knowledge("personnel")
        wep_data = config_provider.get_knowledge("weapons")

        if not geo_data:
            raise CommandError("Geography data is empty (check the admin Knowledge Base).")
        if not pers_data:
            raise CommandError("Personnel data is empty (check the admin Knowledge Base).")
        if not wep_data:
            raise CommandError("Weapons data is empty (check the admin Knowledge Base).")

        knowledge_base = _build_full_knowledge_base(
            geo_data,
            pers_data,
            wep_data,
            max_total_chars=max_knowledge_chars,
        )

        self.stdout.write(
            f"Compiled knowledge base from full dataset ({len(knowledge_base):,} characters)."
        )

        training_template = config_provider.get_prompt_text(
            "training_system", DEFAULT_TRAINING_SYSTEM_PROMPT
        )
        system_prompt = f"{training_template}\n\nKnowledge reference:\n{knowledge_base}"

        modelfile_content = f"""FROM {base_model}

SYSTEM \"\"\"
{system_prompt}
\"\"\"

PARAMETER temperature {UNIFIED_LLM_TRAINING_CONFIG["temperature"]}
PARAMETER top_p {UNIFIED_LLM_TRAINING_CONFIG["top_p"]}
PARAMETER top_k {UNIFIED_LLM_TRAINING_CONFIG["top_k"]}
PARAMETER repeat_penalty {UNIFIED_LLM_TRAINING_CONFIG["repeat_penalty"]}
PARAMETER num_ctx {num_ctx}
PARAMETER num_predict {UNIFIED_LLM_TRAINING_CONFIG["num_predict"]}
"""

        if base_model not in models:
            self.stdout.write(f"Pulling base model {base_model}...")
            try:
                pull_r = requests.post(
                    f"{base_url}/api/pull",
                    json={"name": base_model},
                    timeout=UNIFIED_LLM_TRAINING_CONFIG["ollama_pull_timeout_seconds"],
                )
                if pull_r.status_code != 200:
                    raise CommandError(f"Failed to pull {base_model}")
                self.stdout.write(self.style.SUCCESS(f"Pulled {base_model}"))
            except Exception as e:
                raise CommandError(f"Error pulling model: {e}")

        fd, modelfile_path = tempfile.mkstemp(suffix=".modelfile", text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(modelfile_content)

            self.stdout.write(
                f"Creating custom model {custom_model_name} with context window {num_ctx}..."
            )
            result = subprocess.run(
                ["ollama", "create", custom_model_name, "-f", modelfile_path],
                capture_output=True,
                text=True,
                timeout=UNIFIED_LLM_TRAINING_CONFIG["ollama_create_timeout_seconds"],
            )
            if result.returncode != 0:
                raise CommandError(f"ollama create failed: {result.stderr or result.stdout}")

            self.stdout.write(
                self.style.SUCCESS(
                    f"Unified wargaming model {custom_model_name} created successfully."
                )
            )

            try:
                from orchestrator.services.unified_llm_service import UnifiedLLMService

                svc = UnifiedLLMService(base_url=base_url)
                if svc.check_model_availability():
                    self.stdout.write(self.style.SUCCESS("Model availability check passed."))
                else:
                    self.stdout.write(self.style.WARNING("Model created but availability check failed."))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Post-create check skipped: {e}"))
        finally:
            if os.path.exists(modelfile_path):
                os.unlink(modelfile_path)
