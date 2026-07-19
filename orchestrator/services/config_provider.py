"""
Central access point for admin-editable settings.

Every getter reads from the database first and falls back to the static
values in ``war_game.project_config`` (or the bundled JSON files) so the
service keeps working even before the admin data is seeded or migrated.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from war_game.project_config import (
    GEOGRAPHY_DATA_FILE,
    LLM_PROVIDER_CONFIG,
    PERSONNEL_DATA_FILE,
    UNIFIED_LLM_GENERATION_CONFIG,
    UNIFIED_LLM_TRAINING_CONFIG,
    WEAPONS_DATA_FILE,
)

logger = logging.getLogger(__name__)

_KNOWLEDGE_FILES = {
    "geography": GEOGRAPHY_DATA_FILE,
    "personnel": PERSONNEL_DATA_FILE,
    "weapons": WEAPONS_DATA_FILE,
}


def _get_config():
    """Return the LLMConfig singleton, or None if unavailable."""
    try:
        from orchestrator.models import LLMConfig
        return LLMConfig.load()
    except Exception as exc:  # table missing, app not ready, etc.
        logger.debug("LLMConfig unavailable, using defaults: %s", exc)
        return None


def get_generation_config() -> Dict[str, Any]:
    """Inference parameters, DB-first with static fallback."""
    cfg = _get_config()
    base = dict(UNIFIED_LLM_GENERATION_CONFIG)
    if cfg is None:
        return base
    base.update(
        {
            "temperature": cfg.temperature,
            "top_p": cfg.top_p,
            "num_predict": cfg.num_predict,
            "num_ctx": cfg.num_ctx,
            "repeat_penalty": cfg.repeat_penalty,
            "conversation_history_limit": cfg.conversation_history_limit,
            "request_timeout_seconds": cfg.request_timeout_seconds,
        }
    )
    return base


def get_service_endpoint() -> Dict[str, Any]:
    """Return base_url + served model name, DB-first with static fallback."""
    ollama = (LLM_PROVIDER_CONFIG or {}).get("ollama", {})
    result = {
        "base_url": ollama.get("base_url", "http://localhost:11434"),
        "model_name": ollama.get("wargaming_model", "wargaming:unified"),
    }
    cfg = _get_config()
    if cfg is not None:
        result["base_url"] = cfg.base_url or result["base_url"]
        result["model_name"] = cfg.wargaming_model or result["model_name"]
    return result


def get_training_defaults() -> Dict[str, Any]:
    """Training/build defaults, DB-first for model + base_url."""
    base = dict(UNIFIED_LLM_TRAINING_CONFIG)
    cfg = _get_config()
    if cfg is not None:
        base["default_base_model"] = cfg.base_model or base["default_base_model"]
        base["base_url"] = cfg.base_url or base["base_url"]
        base["num_ctx"] = cfg.num_ctx or base["num_ctx"]
        base["num_predict"] = cfg.num_predict or base["num_predict"]
        base["temperature"] = cfg.temperature or base["temperature"]
        base["repeat_penalty"] = cfg.repeat_penalty or base["repeat_penalty"]
    return base


def get_prompt_text(key: str, default: str) -> str:
    """Return the active prompt text for ``key`` or ``default``."""
    try:
        from orchestrator.models import Prompt
        prompt = Prompt.objects.filter(key=key, is_active=True).first()
        if prompt and prompt.content.strip():
            return prompt.content
    except Exception as exc:
        logger.debug("Prompt '%s' unavailable, using default: %s", key, exc)
    return default


def _load_json_file(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return {}


def get_knowledge(kind: str) -> Dict[str, Any]:
    """Return the dataset for ``kind`` from the DB, else from the JSON file."""
    try:
        from orchestrator.models import KnowledgeBase
        entry = KnowledgeBase.objects.filter(kind=kind).first()
        if entry and entry.data:
            return entry.data
    except Exception as exc:
        logger.debug("KnowledgeBase '%s' unavailable, using file: %s", kind, exc)
    path: Optional[Path] = _KNOWLEDGE_FILES.get(kind)
    return _load_json_file(path) if path else {}
