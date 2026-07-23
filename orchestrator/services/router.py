"""
Pre-processes the user message for context building.
Rule-based only for low latency. Supports both English and Persian input.
"""
import re
from typing import Any, Dict, List


COUNTRY_ALIASES = {
    # English
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
    # Persian (Farsi)
    "سوریه": "syria",
    "عراق": "iraq",
    "ایران": "iran",
    "ایرانی": "iran",
    "اسرائیل": "israel",
    "اسراییل": "israel",
    "رژیم صهیونیستی": "israel",
    "لبنان": "lebanon",
    "اردن": "jordan",
    "عربستان سعودی": "saudi arabia",
    "عربستان": "saudi arabia",
    "سعودی": "saudi arabia",
    "یمن": "yemen",
    "مصر": "egypt",
    "ترکیه": "turkey",
    "ترکیه‌ای": "turkey",
}

COUNTRY_PATTERN = re.compile(
    r"(" + "|".join(sorted((re.escape(k) for k in COUNTRY_ALIASES), key=len, reverse=True)) + r")",
    re.IGNORECASE,
)

# Common non-Middle-East countries (curated). Used to flag questions that fall
# outside the dataset so the prompt can answer briefly and note limited data.
NON_ME_COUNTRY_ALIASES = {
    # English
    "united states": "united states",
    "usa": "united states",
    "america": "united states",
    "american": "united states",
    "russia": "russia",
    "russian": "russia",
    "china": "china",
    "chinese": "china",
    "ukraine": "ukraine",
    "ukrainian": "ukraine",
    "france": "france",
    "french": "france",
    "germany": "germany",
    "german": "germany",
    "britain": "united kingdom",
    "england": "united kingdom",
    "uk": "united kingdom",
    "india": "india",
    "pakistan": "pakistan",
    "north korea": "north korea",
    "south korea": "south korea",
    "japan": "japan",
    # Persian
    "آمریکا": "united states",
    "ایالات متحده": "united states",
    "امریکا": "united states",
    "روسیه": "russia",
    "چین": "china",
    "اوکراین": "ukraine",
    "فرانسه": "france",
    "آلمان": "germany",
    "انگلیس": "united kingdom",
    "انگلستان": "united kingdom",
    "بریتانیا": "united kingdom",
    "هند": "india",
    "پاکستان": "pakistan",
    "کره شمالی": "north korea",
    "کره جنوبی": "south korea",
    "ژاپن": "japan",
    "افغانستان": "afghanistan",
    "آذربایجان": "azerbaijan",
}

NON_ME_COUNTRY_PATTERN = re.compile(
    r"(" + "|".join(sorted((re.escape(k) for k in NON_ME_COUNTRY_ALIASES), key=len, reverse=True)) + r")",
    re.IGNORECASE,
)

GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|yo|good morning|good afternoon|good evening"
    r"|سلام|درود|سلام علیکم|صبح بخیر|ظهر بخیر|عصر بخیر|شب بخیر|وقت بخیر)\b",
    re.IGNORECASE,
)
COMPARE_PATTERN = re.compile(
    r"(compare|comparison|versus|vs\.?|against|difference between|stronger than|weaker than|who would win"
    r"|مقایسه|درگیری|جنگ|نبرد|مقابل|برابر|رویاروی|پیروزی|برنده|قوی‌تر|قوی تر|برتر|قدرتمندتر|کدام یک)",
    re.IGNORECASE,
)
ADVICE_PATTERN = re.compile(
    r"(advice|advise|suggest|recommend|strategy|plan|battle plan|tactics?|how should|what should|best way"
    r"|راهکار|راهبرد|استراتژی|تاکتیک|توصیه|پیشنهاد|بهترین راه|چگونه برتری|چطور برتری|چگونه می‌تواند|چگونه میتواند)",
    re.IGNORECASE,
)
# Explicit war/conflict intent. Used to distinguish a real battle scenario
# (which triggers the بازیکنان/راهکارها structure) from a plain capability
# comparison like "compare the air forces", which should stay flexible.
CONFLICT_PATTERN = re.compile(
    r"(war|battle|conflict|attack|invade|invasion|fight|who would win|would win"
    # جنگ(?!نده) matches "جنگ/جنگی" (war) but NOT "جنگنده" (fighter jet).
    r"|جنگ(?!نده)|نبرد|درگیری|حمله|تهاجم|سناریو|پیروزی|برنده|شکست|مقابله|رویاروی)",
    re.IGNORECASE,
)
QUESTION_PATTERN = re.compile(r"[?؟]\s*$")
PERSIAN_QUESTION_STARTERS = ("آیا", "چگونه", "چطور", "کدام", "چرا", "چه", "چند", "چقدر")

SCENARIO_KEYWORDS = {
    "nuclear": ("nuclear", "atomic", "radiological", "nbc", "هسته‌ای", "هسته ای", "اتمی", "رادیواکتیو"),
    "insurgency": ("insurgency", "insurgent", "guerrilla", "asymmetric", "شورش", "چریکی", "نامتقارن", "پارتیزانی"),
    "urban": ("urban", "city fight", "city battle", "street fighting", "شهری", "جنگ شهری", "نبرد شهری"),
    "mountain": ("mountain", "highland", "elevation", "کوهستان", "کوهستانی", "ارتفاعات"),
    "desert": ("desert", "arid", "صحرا", "صحرایی", "بیابان", "بیابانی", "کویر"),
    "naval": ("naval", "sea", "maritime", "دریایی", "دریا", "نیروی دریایی"),
    "air": ("air war", "airstrike", "air superiority", "air campaign", "air", "هوایی", "نبرد هوایی", "برتری هوایی"),
}

DOMAIN_KEYWORDS = {
    "geography": (
        "terrain", "weather", "geography", "mountain", "desert", "route", "border", "climate",
        "زمین", "جغرافیا", "آب‌وهوا", "آب و هوا", "اقلیم", "مرز", "کوهستان", "صحرا", "زمینی", "توپوگرافی",
    ),
    "personnel": (
        "soldier", "troop", "personnel", "manpower", "reserve", "special forces", "army size",
        "سرباز", "نیرو", "نیروی انسانی", "پرسنل", "ذخیره", "نیروهای ویژه", "اندازه ارتش", "تعداد نیرو",
    ),
    "weapons": (
        "weapon", "tank", "missile", "fighter", "artillery", "drone", "air defense", "navy",
        "تسلیحات", "سلاح", "تانک", "موشک", "جنگنده", "توپخانه", "پهپاد", "پدافند", "ناوگان",
    ),
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
        "جنگنده",
        "جنگنده‌ها",
        "هواپیمای جنگی",
        "نیروی هوایی",
        "برتری هوایی",
    ),
    "drones": ("drone", "drones", "uav", "uavs", "ucav", "ucavs", "پهپاد", "پهپادها", "پرنده بدون سرنشین"),
    "tanks": ("tank", "tanks", "armor", "armored", "armour", "armoured", "تانک", "تانک‌ها", "زرهی", "نفربر"),
    "artillery": ("artillery", "howitzer", "rocket artillery", "mlrs", "توپخانه", "هویتزر", "راکت‌انداز", "خمپاره"),
    "assault_rifles": (
        "assault rifle", "assault rifles", "rifle", "rifles", "small arms",
        "تفنگ", "تفنگ تهاجمی", "سلاح سبک",
    ),
    "sniper_rifles": (
        "sniper", "sniper rifle", "sniper rifles", "marksman rifle",
        "تک‌تیرانداز", "تک تیرانداز", "تفنگ تک‌تیرانداز",
    ),
    "air_defense": (
        "air defense", "air-defence", "anti air", "anti-air", "sam", "surface to air",
        "پدافند", "پدافند هوایی", "ضدهوایی", "ضد هوایی", "سامانه پدافندی",
    ),
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


def _extract_non_me_countries(message: str) -> List[str]:
    matches = [NON_ME_COUNTRY_ALIASES[m.group(1).lower()] for m in NON_ME_COUNTRY_PATTERN.finditer(message)]
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


def _is_greeting(message: str, countries: List[str]) -> bool:
    stripped = message.strip()
    if not stripped or not GREETING_PATTERN.search(stripped):
        return False
    # A greeting is a short opener with no analytical intent. If the user also
    # named countries or asked to compare/advise, treat it as a real question.
    if countries:
        return False
    if COMPARE_PATTERN.search(stripped) or ADVICE_PATTERN.search(stripped):
        return False
    return len(stripped) <= 40


def _detect_message_type(message: str, countries: List[str]) -> str:
    stripped = message.strip()
    if not stripped:
        return "empty"
    if _is_greeting(message, countries):
        return "greeting"
    if COMPARE_PATTERN.search(message) and len(countries) >= 2:
        return "comparison"
    if ADVICE_PATTERN.search(message) and (
        "battle" in message.lower() or "war" in message.lower()
        or "جنگ" in message or "نبرد" in message or "درگیری" in message
        or countries
    ):
        return "battle_advice"
    if (
        QUESTION_PATTERN.search(stripped)
        or stripped.lower().startswith(
            ("what", "which", "who", "how", "why", "when", "can", "could", "would", "should")
        )
        or stripped.startswith(PERSIAN_QUESTION_STARTERS)
    ):
        return "question"
    return "analysis"


def _build_processed_message(
    message: str,
    countries: List[str],
    non_me_countries: List[str],
    scenario: str,
    message_type: str,
    focus: List[str],
    is_battle_scenario: bool,
) -> str:
    stripped = " ".join(message.strip().split())
    if message_type == "greeting":
        return (
            "The user is greeting the assistant. Introduce yourself briefly as a military "
            "advisor, list what you can analyze, and invite a wargaming scenario. Do not dump data."
        )

    details = []
    if countries:
        display_countries = [country.title() for country in countries]
        if is_battle_scenario and len(display_countries) >= 2:
            details.append(
                f"Battle/conflict scenario between {display_countries[0]} and {display_countries[1]}. "
                f"Use the required battle-scenario output structure"
            )
        elif message_type == "comparison" and len(display_countries) >= 2:
            details.append(f"Compare {display_countries[0]} and {display_countries[1]}")
        elif message_type == "battle_advice" and len(display_countries) >= 2:
            details.append(f"Assess a battle between {display_countries[0]} and {display_countries[1]}")
        else:
            details.append(f"Analyze {', '.join(display_countries)}")
    else:
        details.append("Answer the user's military analysis request")

    if message_type == "battle_advice":
        details.append("provide practical battle advice and strategy considerations with justification")
    elif message_type == "comparison":
        details.append("provide a decisive side-by-side comparison with a clear final judgement and reasons")
    elif message_type == "question":
        details.append("answer the question directly")
    else:
        details.append("provide a clear analytical answer")

    if focus and focus != ["general"]:
        details.append(f"focus on {', '.join(focus)}")
    if scenario != "conventional":
        details.append(f"for a {scenario} scenario")
    if non_me_countries:
        details.append(
            f"Note: {', '.join(c.title() for c in non_me_countries)} are outside the dataset; "
            f"answer briefly and state that detailed data is limited"
        )

    details.append(f'Original user message: "{stripped}"')
    return ". ".join(details) + "."


def _route(message: str) -> Dict[str, Any]:
    countries = _extract_countries(message)
    non_me_countries = _extract_non_me_countries(message)
    scenario = _detect_scenario(message)
    focus = _detect_focus(message)
    weapon_subtypes = _detect_weapon_subtypes(message)
    message_type = _detect_message_type(message, countries)
    # A battle scenario needs two countries AND explicit conflict intent
    # (battle_advice, or war/conflict wording). A plain "compare X and Y" is not one.
    is_battle_scenario = len(countries) >= 2 and (
        message_type == "battle_advice" or bool(CONFLICT_PATTERN.search(message))
    )
    processed_message = _build_processed_message(
        message, countries, non_me_countries, scenario, message_type, focus, is_battle_scenario
    )

    return {
        "countries": countries,
        "country_count": len(countries),
        "country_pair": countries[:2],
        "non_me_countries": non_me_countries,
        "has_non_me": bool(non_me_countries),
        "scenario": scenario,
        "message_type": message_type,
        "is_battle_scenario": is_battle_scenario,
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
