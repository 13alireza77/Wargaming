"""
Pre-processes the user message for context building.
Rule-based only for low latency.
"""
import re
from typing import Any, Dict, List


COUNTRY_ALIASES = {
    "syria": "syria",
    "syrian": "syria",
    "iraq": "iraq",
    "iraqi": "iraq",
    "iran": "iran",
    "iranian": "iran",
    "israel": "israel",
    "israeli": "israel",
    "lebanon": "lebanon",
    "lebanese": "lebanon",
    "jordan": "jordan",
    "jordanian": "jordan",
    "saudi arabia": "saudi arabia",
    "saudi": "saudi arabia",
    "yemen": "yemen",
    "yemeni": "yemen",
    "egypt": "egypt",
    "egyptian": "egypt",
    "turkey": "turkey",
    "turkish": "turkey",
}

COUNTRY_PATTERN = re.compile(
    r"\b(" + "|".join(sorted((re.escape(k) for k in COUNTRY_ALIASES), key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|yo|good morning|good afternoon|good evening)\b[!. ]*$",
    re.IGNORECASE,
)
COMPARE_PATTERN = re.compile(
    r"\b(compare|comparison|versus|vs\.?|against|difference between|stronger than|weaker than|who would win)\b",
    re.IGNORECASE,
)
ADVICE_PATTERN = re.compile(
    r"\b(advice|advise|suggest|recommend|strategy|plan|battle plan|tactics?|how should|what should|best way)\b",
    re.IGNORECASE,
)
QUESTION_PATTERN = re.compile(r"\?$")

SCENARIO_KEYWORDS = {
    "nuclear": ("nuclear", "atomic", "radiological", "nbc"),
    "insurgency": ("insurgency", "insurgent", "guerrilla", "asymmetric"),
    "urban": ("urban", "city fight", "city battle", "street fighting"),
    "mountain": ("mountain", "highland", "elevation"),
    "desert": ("desert", "arid"),
    "naval": ("naval", "sea", "maritime"),
    "air": ("air war", "airstrike", "air superiority", "air campaign", "air"),
}

DOMAIN_KEYWORDS = {
    "geography": ("terrain", "weather", "geography", "mountain", "desert", "route", "border", "climate"),
    "personnel": ("soldier", "troop", "personnel", "manpower", "reserve", "special forces", "army size"),
    "weapons": ("weapon", "tank", "missile", "fighter", "artillery", "drone", "air defense", "navy"),
}

WEAPON_SUBTYPE_KEYWORDS = {
    "fighter_jets": (
        "fighter",
        "fighters",
        "fighter jet",
        "fighter jets",
        "air fighter",
        "air fighters",
        "jet",
        "jets",
        "aircraft",
        "combat aircraft",
        "air force",
        "dogfight",
        "dogfights",
        "air combat",
        "air war",
        "air superiority",
    ),
    "drones": ("drone", "drones", "uav", "uavs", "ucav", "ucavs"),
    "tanks": ("tank", "tanks", "armor", "armored", "armour", "armoured"),
    "artillery": ("artillery", "howitzer", "rocket artillery", "mlrs"),
    "assault_rifles": ("assault rifle", "assault rifles", "rifle", "rifles", "small arms"),
    "sniper_rifles": ("sniper", "sniper rifle", "sniper rifles", "marksman rifle"),
    "air_defense": ("air defense", "air-defence", "anti air", "anti-air", "sam", "surface to air"),
}


def _dedupe(values: List[str]) -> List[str]:
    seen = set()
    ordered = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _extract_countries(message: str) -> List[str]:
    matches = [COUNTRY_ALIASES[m.group(1).lower()] for m in COUNTRY_PATTERN.finditer(message)]
    return _dedupe(matches)


def _detect_scenario(message: str) -> str:
    msg_lower = message.lower()
    for scenario, keywords in SCENARIO_KEYWORDS.items():
        if any(keyword in msg_lower for keyword in keywords):
            return scenario
    return "conventional"


def _detect_focus(message: str) -> List[str]:
    msg_lower = message.lower()
    focus = []
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in msg_lower for keyword in keywords):
            focus.append(domain)
    return focus or ["general"]


def _detect_weapon_subtypes(message: str) -> List[str]:
    msg_lower = message.lower()
    subtypes = []
    for subtype, keywords in WEAPON_SUBTYPE_KEYWORDS.items():
        if any(keyword in msg_lower for keyword in keywords):
            subtypes.append(subtype)
    return subtypes


def _detect_message_type(message: str, countries: List[str]) -> str:
    stripped = message.strip()
    if not stripped:
        return "empty"
    if GREETING_PATTERN.match(stripped):
        return "greeting"
    if COMPARE_PATTERN.search(message) and len(countries) >= 2:
        return "comparison"
    if ADVICE_PATTERN.search(message) and ("battle" in message.lower() or "war" in message.lower() or countries):
        return "battle_advice"
    if QUESTION_PATTERN.search(stripped) or stripped.lower().startswith(
        ("what", "which", "who", "how", "why", "when", "can", "could", "would", "should")
    ):
        return "question"
    return "analysis"


def _build_processed_message(message: str, countries: List[str], scenario: str, message_type: str, focus: List[str]) -> str:
    stripped = " ".join(message.strip().split())
    if message_type == "greeting":
        return "The user is greeting the assistant. Respond briefly, warmly, and invite a wargaming question."

    details = []
    if countries:
        display_countries = [country.title() for country in countries]
        if message_type == "comparison" and len(display_countries) >= 2:
            details.append(f"Compare {display_countries[0]} and {display_countries[1]}")
        elif message_type == "battle_advice" and len(display_countries) >= 2:
            details.append(f"Assess a battle between {display_countries[0]} and {display_countries[1]}")
        else:
            details.append(f"Analyze {', '.join(display_countries)}")
    else:
        details.append("Answer the user's military analysis request")

    if message_type == "battle_advice":
        details.append("provide practical battle advice and strategy considerations")
    elif message_type == "comparison":
        details.append("provide a side-by-side comparison with likely advantages and disadvantages")
    elif message_type == "question":
        details.append("answer the question directly")
    else:
        details.append("provide a clear analytical answer")

    if focus and focus != ["general"]:
        details.append(f"focus on {', '.join(focus)}")
    if scenario != "conventional":
        details.append(f"for a {scenario} scenario")

    details.append(f'Original user message: "{stripped}"')
    return ". ".join(details) + "."


def _route(message: str) -> Dict[str, Any]:
    countries = _extract_countries(message)
    scenario = _detect_scenario(message)
    focus = _detect_focus(message)
    weapon_subtypes = _detect_weapon_subtypes(message)
    message_type = _detect_message_type(message, countries)
    processed_message = _build_processed_message(message, countries, scenario, message_type, focus)

    return {
        "countries": countries,
        "country_count": len(countries),
        "country_pair": countries[:2],
        "scenario": scenario,
        "message_type": message_type,
        "focus": focus,
        "weapon_subtypes": weapon_subtypes,
        "processed_message": processed_message,
        "original_message": message.strip(),
    }


class Router:
    """Pre-processes the user message into lightweight routing metadata."""

    def route(self, message: str) -> Dict[str, Any]:
        """
        Return routing hints for the orchestrator and unified model.
        """
        return _route(message)
