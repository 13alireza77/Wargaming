"""
Unified wargaming LLM: one Ollama call with combined geography, personnel, and weapons context.
Tuned for local models where predictable latency matters.
"""
import json
import logging
from typing import Any, Dict, Iterator, List, Optional, Set, Tuple

import requests

from . import config_provider

logger = logging.getLogger(__name__)


class StreamLLMError(Exception):
    """Raised when a streaming Ollama request fails."""

# Built-in default; the admin-editable prompt (key="unified_system") overrides this.
UNIFIED_SYSTEM_PROMPT = """You are a Middle East wargaming analyst with access to geography, personnel, and weapons data.

Language:
- The context data below is written in English, but you MUST always respond in fluent, natural Persian (Farsi) unless the user explicitly writes in English.
- Write in clear, formal, native-quality Persian suitable for military analysis. Do NOT mix English words into Persian sentences, except for standard proper nouns and equipment names (e.g. F-16, S-300), which you may keep in their common form.
- Translate all analysis, reasoning, numbers context, and terrain/personnel/weapons descriptions into Persian.

Rules:
- Answer directly and fully (400–600 words max).
- Use ONLY provided context when possible. Do not invent numbers, units, or facts. If data is missing, state it.
- Match response to query type:
  • comparison → clear side-by-side + final judgement  
  • who would win → decisive answer with reasoning  
  • terrain → geography-focused analysis  
  • weapons → systems + effectiveness  
  • personnel → manpower, structure, readiness  
  • battle_advice → practical, high-level strategy (no certainty claims)

- Use specific data (numbers, locations, units) when available.
- Structure clearly (paragraphs or concise bullets). Avoid repetition or templates.
- If greeting → brief Persian welcome, then guide user to ask about scenarios, countries, or analysis.
"""


def _lookup_country_entry(data_map: Dict[str, Any], country: str) -> Optional[Dict[str, Any]]:
    country_key = country.lower().replace(" ", "_")
    if country_key in data_map:
        return data_map[country_key]
    for _, value in data_map.items():
        if value.get("name", "").lower() == country.lower():
            return value
    return None


def _build_geography_context(
        data: Dict[str, Any],
        countries: List[str],
        include_summary: bool = False,
) -> str:
    regions = data.get("regions", {})
    parts = []

    for country in countries:
        region = _lookup_country_entry(regions, country)
        if not region:
            continue
        name = region.get("name", country.title())
        terrain = region.get("terrain", {}).get("description", "")
        weather = region.get("weather", {}).get("climate", "")
        advantages = region.get("military_considerations", {}).get("terrain_advantages", [])[:3]
        disadvantages = region.get("military_considerations", {}).get("terrain_disadvantages", [])[:2]
        defensive = region.get("military_considerations", {}).get("defensive_positions", [])[:2]
        offensive = region.get("military_considerations", {}).get("offensive_routes", [])[:2]
        urban = region.get("strategic_features", {}).get("urban_centers", [])[:3]
        parts.append(
            f"{name}: {terrain}. Climate: {weather}. Advantages: {', '.join(advantages)}. "
            f"Disadvantages: {', '.join(disadvantages)}. Defensive: {', '.join(defensive)}. "
            f"Offensive routes: {', '.join(offensive)}. Key cities: {', '.join(urban)}."
        )

    if include_summary:
        summary_bits = []
        chokepoints = data.get("strategic_chokepoints", {}) or {}
        infrastructure = data.get("infrastructure", {}) or {}
        weather_patterns = data.get("weather_patterns", {}) or {}
        if chokepoints:
            summary_bits.append(f"Strategic chokepoints: {', '.join(list(chokepoints.keys())[:5])}.")
        if infrastructure:
            summary_bits.append(f"Infrastructure factors: {', '.join(list(infrastructure.keys())[:5])}.")
        if weather_patterns:
            summary_bits.append(f"Regional weather patterns: {', '.join(list(weather_patterns.keys())[:5])}.")
        if summary_bits:
            parts.append(" ".join(summary_bits))

    return " ".join(part for part in parts if part).strip()


def _build_personnel_context(
        data: Dict[str, Any],
        countries: List[str],
        include_summary: bool = False,
) -> str:
    countries_data = data.get("personnel_data", {}).get("countries", {})
    parts = []

    for country in countries:
        country_entry = _lookup_country_entry(countries_data, country)
        if not country_entry:
            continue
        name = country_entry.get("name", country.title())
        total = country_entry.get("total_personnel", "N/A")
        active = country_entry.get("active_duty", "N/A")
        reserves = country_entry.get("reserves", "N/A")
        branches = ", ".join((country_entry.get("branches") or {}).keys())
        special_units = []
        for _, branch in (country_entry.get("branches") or {}).items():
            for unit_name, unit in (branch.get("special_units") or {}).items():
                special_units.append(f"{unit_name}: {unit.get('quantity', '?')}")
        special_str = "; ".join(special_units[:4]) if special_units else "N/A"
        parts.append(
            f"{name}: total {total}, active {active}, reserves {reserves}. "
            f"Branches: {branches}. Special units: {special_str}."
        )

    if include_summary:
        summary_bits = []
        branch_characteristics = data.get("branch_characteristics", {}) or {}
        rank_hierarchy = data.get("rank_hierarchy", {}) or {}
        if branch_characteristics:
            summary_bits.append(
                f"Branch characteristics available for: {', '.join(list(branch_characteristics.keys())[:5])}."
            )
        if rank_hierarchy:
            summary_bits.append(f"Rank hierarchy branches: {', '.join(list(rank_hierarchy.keys())[:5])}.")
        if summary_bits:
            parts.append(" ".join(summary_bits))

    return " ".join(part for part in parts if part).strip()


def _build_weapons_context(
        data: Dict[str, Any],
        countries: List[str],
        weapon_subtypes: Optional[List[str]] = None,
        include_summary: bool = False,
) -> str:
    categories = data.get("weapon_categories", {})
    parts = []
    requested_subtypes: Set[str] = set(weapon_subtypes or [])

    for country in countries:
        country_key = country.lower().replace(" ", "_")
        holdings = []
        for category_key, cat in categories.items():
            for type_name, wtype in (cat.get("types") or {}).items():
                if requested_subtypes and type_name not in requested_subtypes:
                    continue
                country_data = (wtype.get("countries") or {}).get(country_key)
                if not country_data:
                    continue
                models = country_data.get("primary_models", []) or country_data.get("models", [])
                effectiveness = wtype.get("effectiveness", "")
                snippet = wtype.get("name", type_name)
                if models:
                    snippet += f": {', '.join(models)}"
                if effectiveness:
                    snippet += f" (effectiveness: {effectiveness})"
                holdings.append(snippet)
        if holdings:
            parts.append(f"{country.title()}: {'; '.join(holdings[:8])}.")
        elif requested_subtypes:
            requested_display = ", ".join(subtype.replace("_", " ") for subtype in sorted(requested_subtypes))
            parts.append(f"{country.title()}: no specific data found for {requested_display}.")

    if include_summary:
        category_summaries = []
        for category_key, cat in categories.items():
            name = cat.get("name")
            description = cat.get("description")
            if name and description:
                category_summaries.append(f"{name}: {description}")
        if category_summaries:
            parts.append("Available weapon domains: " + " ".join(category_summaries[:5]))

    return " ".join(part for part in parts if part).strip()


def _should_include_domain(focus: List[str], message_type: str, countries: List[str], domain: str) -> bool:
    if message_type == "greeting":
        return False
    if "general" in focus:
        return bool(countries) or message_type in {"comparison", "battle_advice", "analysis", "question"}
    return domain in focus


def _should_include_summary(focus: List[str], countries: List[str]) -> bool:
    return not countries or "general" in focus


def _generation_options_for_intent(intent: Dict[str, Any]) -> Dict[str, Any]:
    gen = config_provider.get_generation_config()
    return {
        "temperature": gen["temperature"],
        "top_p": gen["top_p"],
        "num_predict": gen["num_predict"],
        "num_ctx": gen["num_ctx"],
        "repeat_penalty": gen["repeat_penalty"],
    }


class UnifiedLLMService:
    """Single inference service: load 3 JSONs, build context from intent, one Ollama call."""

    def __init__(
            self,
            model_name: Optional[str] = None,
            base_url: Optional[str] = None,
            timeout: Optional[int] = None,
    ):
        endpoint = config_provider.get_service_endpoint()
        self.base_url = base_url or endpoint["base_url"]
        self.model_name = model_name or endpoint["model_name"]
        config_timeout = config_provider.get_generation_config()["request_timeout_seconds"]
        self.timeout = config_timeout if timeout is None else min(timeout, config_timeout)
        self._geography_data: Optional[Dict[str, Any]] = None
        self._personnel_data: Optional[Dict[str, Any]] = None
        self._weapons_data: Optional[Dict[str, Any]] = None

    def _load_data(self) -> None:
        if self._geography_data is not None:
            return
        self._geography_data = config_provider.get_knowledge("geography")
        self._personnel_data = config_provider.get_knowledge("personnel")
        self._weapons_data = config_provider.get_knowledge("weapons")

    def _build_context_block(self, intent: Dict[str, Any]) -> str:
        countries = intent.get("countries") or []
        scenario = intent.get("scenario", "conventional")
        message_type = intent.get("message_type", "analysis")
        focus = intent.get("focus") or ["general"]
        weapon_subtypes = intent.get("weapon_subtypes") or []
        processed_message = intent.get("processed_message", "")

        self._load_data()
        include_summary = _should_include_summary(focus, countries)
        parts = [f"Scenario: {scenario}.", f"Message type: {message_type}.", f"Focus: {', '.join(focus)}."]

        if countries:
            parts.append(f"Countries in scope: {', '.join(countries)}.")
        if processed_message:
            parts.append(f"Routing guidance: {processed_message}")

        if _should_include_domain(focus, message_type, countries, "geography"):
            geo = _build_geography_context(
                self._geography_data or {},
                countries,
                include_summary=include_summary,
            )
            if geo:
                parts.append(f"Geography: {geo}")

        if _should_include_domain(focus, message_type, countries, "personnel"):
            personnel = _build_personnel_context(
                self._personnel_data or {},
                countries,
                include_summary=include_summary,
            )
            if personnel:
                parts.append(f"Personnel: {personnel}")

        if _should_include_domain(focus, message_type, countries, "weapons"):
            weapons = _build_weapons_context(
                self._weapons_data or {},
                countries,
                weapon_subtypes=weapon_subtypes,
                include_summary=include_summary,
            )
            if weapons:
                parts.append(f"Weapons: {weapons}")

        return "\n".join(parts)

    def _prepare_messages(
            self,
            message: str,
            conversation_context: Optional[List[Dict[str, str]]] = None,
            intent: Optional[Dict[str, Any]] = None,
    ) -> Tuple[List[Dict[str, str]], Dict[str, Any]]:
        from .router import Router

        router = Router()
        resolved_intent = intent if intent is not None else router.route(message)
        context_block = self._build_context_block(resolved_intent)

        user_content = f"{message}"
        if context_block.strip():
            user_content = f"Context:\n{context_block}\n\nUser question:\n{message}"

        system_prompt = config_provider.get_prompt_text("unified_system", UNIFIED_SYSTEM_PROMPT)
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_context:
            history_limit = config_provider.get_generation_config()["conversation_history_limit"]
            for msg in conversation_context[-history_limit:]:
                role = msg.get("role")
                content = msg.get("content")
                if role and content and role in ("user", "assistant"):
                    messages.append({"role": role, "content": (content or "")[:800]})
        messages.append({"role": "user", "content": user_content})
        return messages, resolved_intent

    def analyze_stream(
            self,
            message: str,
            conversation_context: Optional[List[Dict[str, str]]] = None,
            intent: Optional[Dict[str, Any]] = None,
    ) -> Iterator[str]:
        """Stream token chunks from Ollama."""
        messages, resolved_intent = self._prepare_messages(message, conversation_context, intent)
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
            "options": _generation_options_for_intent(resolved_intent),
        }
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout,
            ) as response:
                response.raise_for_status()
                for line in response.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    data = json.loads(line)
                    chunk = data.get("message", {}).get("content", "")
                    if chunk:
                        yield chunk
                    if data.get("done"):
                        return
        except requests.exceptions.Timeout:
            logger.warning("Unified LLM stream timed out (limit %ss)", self.timeout)
            raise StreamLLMError("Request timed out. Please try again.") from None
        except requests.exceptions.RequestException as e:
            logger.warning("Unified LLM stream failed: %s", e)
            raise StreamLLMError(str(e)) from e
        except Exception as e:
            logger.exception("Unified LLM analyze_stream failed")
            raise StreamLLMError(str(e)) from e

    def analyze(
            self,
            message: str,
            conversation_context: Optional[List[Dict[str, str]]] = None,
            intent: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Single Ollama call. Returns { "success", "reply", "sources" }.
        """
        messages, resolved_intent = self._prepare_messages(message, conversation_context, intent)

        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": False,
            "options": _generation_options_for_intent(resolved_intent),
        }
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            r.raise_for_status()
            reply = r.json().get("message", {}).get("content", "").strip()
            logger.debug("Unified LLM reply (%d chars)", len(reply))
            return {
                "success": True,
                "reply": reply or "I couldn't generate a response. Please try again.",
                "sources": ["geography", "personnel", "weapons"],
            }
        except requests.exceptions.Timeout:
            logger.warning("Unified LLM request timed out (limit %ss)", self.timeout)
            return {
                "success": False,
                "reply": "",
                "sources": [],
                "error": "Request timed out. Please try again.",
            }
        except requests.exceptions.RequestException as e:
            logger.warning("Unified LLM request failed: %s", e)
            return {
                "success": False,
                "reply": "",
                "sources": [],
                "error": str(e),
            }
        except Exception as e:
            logger.exception("Unified LLM analyze failed")
            return {
                "success": False,
                "reply": "",
                "sources": [],
                "error": str(e),
            }

    def check_model_availability(self) -> bool:
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if r.status_code != 200:
                return False
            models = r.json().get("models", [])
            return any(m.get("name") == self.model_name for m in models)
        except Exception:
            return False
