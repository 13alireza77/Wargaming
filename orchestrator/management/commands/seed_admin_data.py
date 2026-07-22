"""
Seed admin-editable data (LLM config, prompts, knowledge datasets) from the
existing project constants and JSON files.

Idempotent: existing rows are left untouched unless --force is passed.
"""
import json
from pathlib import Path
from typing import Any, Dict

from django.core.management.base import BaseCommand

from orchestrator.management.commands.retrain_wargaming_llm import (
    DEFAULT_TRAINING_SYSTEM_PROMPT,
)
from orchestrator.models import KnowledgeBase, LLMConfig, Prompt
from orchestrator.services.unified_llm_service import UNIFIED_SYSTEM_PROMPT
from war_game.project_config import (
    GEOGRAPHY_DATA_FILE,
    LLM_PROVIDER_CONFIG,
    PERSONNEL_DATA_FILE,
    UNIFIED_LLM_GENERATION_CONFIG,
    UNIFIED_LLM_TRAINING_CONFIG,
    WEAPONS_DATA_FILE,
)

_KNOWLEDGE_FILES = {
    "geography": GEOGRAPHY_DATA_FILE,
    "personnel": PERSONNEL_DATA_FILE,
    "weapons": WEAPONS_DATA_FILE,
}


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


class Command(BaseCommand):
    help = "Seed LLM config, prompts and knowledge datasets from files/constants."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Overwrite existing rows with the values from files/constants.",
        )
        parser.add_argument(
            "--prompts-only",
            action="store_true",
            help="Update only Prompt rows (skip LLM config and knowledge datasets).",
        )

    def handle(self, *args, **options):
        force = options["force"]
        prompts_only = options["prompts_only"]
        if not prompts_only:
            self._seed_config(force)
        self._seed_prompts(force)
        if not prompts_only:
            self._seed_knowledge(force)
        self.stdout.write(self.style.SUCCESS("Admin data seeding complete."))

    def _seed_config(self, force: bool):
        config, created = LLMConfig.objects.get_or_create(pk=1)
        if not created and not force:
            self.stdout.write("LLM config already exists (use --force to reset).")
            return
        ollama = (LLM_PROVIDER_CONFIG or {}).get("ollama", {})
        config.provider = LLM_PROVIDER_CONFIG.get("provider", "ollama")
        config.base_url = ollama.get("base_url", config.base_url)
        config.base_model = UNIFIED_LLM_TRAINING_CONFIG.get("default_base_model", config.base_model)
        config.wargaming_model = ollama.get("wargaming_model", config.wargaming_model)
        config.temperature = UNIFIED_LLM_GENERATION_CONFIG["temperature"]
        config.top_p = UNIFIED_LLM_GENERATION_CONFIG["top_p"]
        config.num_predict = UNIFIED_LLM_GENERATION_CONFIG["num_predict"]
        config.num_ctx = UNIFIED_LLM_GENERATION_CONFIG["num_ctx"]
        config.repeat_penalty = UNIFIED_LLM_GENERATION_CONFIG["repeat_penalty"]
        config.conversation_history_limit = UNIFIED_LLM_GENERATION_CONFIG["conversation_history_limit"]
        config.request_timeout_seconds = UNIFIED_LLM_GENERATION_CONFIG["request_timeout_seconds"]
        config.save()
        self.stdout.write(self.style.SUCCESS(f"LLM config {'created' if created else 'reset'}."))

    def _seed_prompts(self, force: bool):
        prompts = {
            "unified_system": ("Runtime system prompt", UNIFIED_SYSTEM_PROMPT),
            "training_system": ("Training system prompt", DEFAULT_TRAINING_SYSTEM_PROMPT),
        }
        for key, (title, content) in prompts.items():
            obj, created = Prompt.objects.get_or_create(
                key=key,
                defaults={"title": title, "content": content, "is_active": True},
            )
            if not created and force:
                obj.title = title
                obj.content = content
                obj.save()
            state = "created" if created else ("reset" if force else "kept")
            self.stdout.write(f"Prompt '{key}': {state}.")

    def _seed_knowledge(self, force: bool):
        for kind, path in _KNOWLEDGE_FILES.items():
            data = _load_json(path)
            obj, created = KnowledgeBase.objects.get_or_create(
                kind=kind,
                defaults={"data": data},
            )
            if not created and force:
                obj.data = data
                obj.save()
            state = "created" if created else ("reset" if force else "kept")
            self.stdout.write(f"Knowledge '{kind}': {state} ({len(data)} sections).")
