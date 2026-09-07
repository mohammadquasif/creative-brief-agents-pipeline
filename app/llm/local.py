"""Deterministic, zero-dependency provider used by default.

No network calls, no API keys, fully reproducible — ideal for demos and tests.

Design principle: the heuristics are deliberately *conservative*. If a field
cannot be found with reasonable confidence it is simply left out of the dict,
and the validation layer decides what happens next:

    first parse -> (issues?) -> repair pass -> fallback defaults -> error

This mirrors what a real model would do (only less imaginative).
"""
from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Any

from ..schemas.brief import CreativeBrief, Tone, TONE_SYNONYMS
from ..schemas.validation import ValidationIssue
from .base import LLMProvider

# --------------------------------------------------------------------------- #
# Static knowledge tables (kept near the heuristics so they are easy to tune) #
# --------------------------------------------------------------------------- #

_WEEKDAYS: dict[str, int] = {
    "monday": 0, "mon": 0,
    "tuesday": 1, "tue": 1, "tues": 1,
    "wednesday": 2, "wed": 2,
    "thursday": 3, "thu": 3, "thur": 3, "thurs": 3,
    "friday": 4, "fri": 4,
    "saturday": 5, "sat": 5,
    "sunday": 6, "sun": 6,
}

_MONTHS: dict[str, int] = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

#: word/phrase -> marketing audience label
_AUDIENCE: list[tuple[str, str]] = [
    ("gen alpha", "Gen Alpha"),
    ("gen z", "Gen Z"),
    ("gen-z", "Gen Z"),
    ("genz", "Gen Z"),
    ("millennials", "Millennials"),
    ("young professionals", "Young Professionals"),
    ("working professionals", "Working Professionals"),
    ("professionals", "Working Professionals"),
    ("college students", "College Students"),
    ("college", "College Students"),
    ("students", "Students"),
    ("teenagers", "Teens"),
    ("teens", "Teens"),
    ("fitness enthusiasts", "Fitness Enthusiasts"),
    ("parents", "Parents"),
    ("moms", "Moms"),
    ("dads", "Dads"),
    ("athletes", "Athletes"),
    ("runners", "Runners"),
    ("gamers", "Gamers"),
    ("foodies", "Foodies"),
    ("families", "Families"),
    ("boomers", "Baby Boomers"),
]

#: keyword -> product label used to name the campaign / draft a key message.
#: Longer / more specific entries are matched first.
_PRODUCTS: list[tuple[str, str]] = [
    ("new sneaker drop", "Sneaker Drop"),
    ("sneaker drop", "Sneaker Drop"),
    ("sneakers", "Sneaker Drop"),
    ("sneaker", "Sneaker Drop"),
    ("energy drink", "Energy Drink Launch"),
    ("headphones", "Headphones Launch"),
    ("headphone", "Headphones Launch"),
    ("smartphone", "Smartphone Launch"),
    ("streetwear", "Streetwear Drop"),
    ("fragrance", "Fragrance Launch"),
    ("perfume", "Fragrance Launch"),
    ("cologne", "Fragrance Launch"),
    ("skincare", "Skincare Launch"),
    ("clothing", "Clothing Drop"),
    ("fashion", "Fashion Collection"),
    ("beauty", "Beauty Launch"),
    ("workout", "Workout Launch"),
    ("fitness", "Fitness Launch"),
    ("coffee", "Coffee Launch"),
    ("gaming", "Gaming Launch"),
    ("phone", "Smartphone Launch"),
    ("shoes", "Shoe Launch"),
    ("shoe", "Shoe Launch"),
    ("game", "Game Launch"),
    ("car", "Car Launch"),
    ("app", "App Launch"),
]

#: tone -> default consumer key-message template (used when no explicit message)
_KEY_TEMPLATES: dict[Tone, str] = {
    Tone.HYPE: "The {p} is live — limited pairs, no restocks. Don't sleep on it.",
    Tone.LUXURY: "Introducing the {p} — quietly refined, unmistakably yours.",
    Tone.PLAYFUL: "Say hello to the {p} — your new favourite just landed!",
    Tone.PROFESSIONAL: "Meet the {p}: engineered to perform, designed to impress.",
    Tone.EMOTIONAL: "The {p} you have been waiting for is finally here.",
    Tone.SUSTAINABLE: "The {p}, made with the planet in mind — feel good, move better.",
    Tone.RETRO: "Throw it back with the {p} — the icon is back.",
    Tone.MINIMAL: "The {p}. Nothing extra. Everything you need.",
    Tone.EDGY: "Break the rules with the {p}. Zero apologies.",
}

#: tone -> call-to-action line + extra hashtags used by the generator
_GEN_STYLE: dict[Tone, dict[str, Any]] = {
    Tone.HYPE: {
        "cta": "Don't sleep — cop yours before they're gone.",
        "tags": ["#NewDrop", "#CopOrMiss"],
    },
    Tone.LUXURY: {
        "cta": "An invitation, not an announcement.",
        "tags": ["#LimitedEdition", "#Timeless"],
    },
    Tone.PLAYFUL: {
        "cta": "Come say hi — you're going to love it.",
        "tags": ["#GoodVibes", "#NewFavourite"],
    },
    Tone.PROFESSIONAL: {
        "cta": "Learn more and get in touch today.",
        "tags": ["#Launch", "#BuiltToPerform"],
    },
    Tone.EMOTIONAL: {
        "cta": "You deserve this one.",
        "tags": ["#MadeForYou", "#FeelTheMoment"],
    },
    Tone.SUSTAINABLE: {
        "cta": "Make the choice that feels as good as it looks.",
        "tags": ["#MadeResponsibly", "#BetterFuture"],
    },
    Tone.RETRO: {
        "cta": "Back by popular demand.",
        "tags": ["#Throwback", "#IconReturns"],
    },
    Tone.MINIMAL: {
        "cta": "Now available. Nothing extra.",
        "tags": ["#SimplyBetter", "#NowAvailable"],
    },
    Tone.EDGY: {
        "cta": "No rules. Just you.",
        "tags": ["#NoRules", "#BreakTheMould"],
    },
}

# --------------------------------------------------------------------------- #
# Parsing helpers                                                             #
# --------------------------------------------------------------------------- #


def _next_weekday(target_weekday: int, *, after: date | None = None) -> date:
    """First occurrence of ``target_weekday`` strictly after today."""
    today = after or date.today()
    days_ahead = (target_weekday - today.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return today + timedelta(days=days_ahead)


def _try_date(year: int, month: int, day: int) -> date | None:
    try:
        return date(year, month, day)
    except ValueError:
        return None


def _parse_deadline(raw: str) -> date | None:
    """Resolve deadline mentions into an actual :class:`date` or ``None``."""
    text = raw.lower()
    today = date.today()

    # 1) Explicit ISO-ish dates: 2026-09-11 / 2026/09/11
    for m in re.finditer(r"\b(\d{4})[-/](\d{1,2})[-/](\d{1,2})\b", text):
        d = _try_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if d:
            return d

    # 2) Month-name forms: "September 11" / "sept 11" / "11 September"
    for name, month in sorted(_MONTHS.items(), key=lambda kv: len(kv[0]), reverse=True):
        for m in re.finditer(rf"\b{name}\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", text):
            d = _try_date(today.year, month, int(m.group(1)))
            if d and d >= today:
                return d
        for m in re.finditer(rf"\b(\d{{1,2}})\s+{name}\b", text):
            d = _try_date(today.year, month, int(m.group(1)))
            if d and d >= today:
                return d

    # 3) Numeric month/day/year (US-friendly: MM/DD/YYYY). Tolerant to DD/MM.
    for m in re.finditer(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b", text):
        first, second, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        for a, b in ((first, second), (second, first)):
            if 1 <= a <= 12:
                d = _try_date(year, a, b)
                if d:
                    return d

    # 4) Relative phrasing
    if re.search(r"\bnext week\b", text):
        return today + timedelta(days=7)
    if re.search(r"\b(end of (the )?week|by eow|this week)\b", text):
        return _next_weekday(_WEEKDAYS["friday"])
    if re.search(r"\btomorrow\b", text):
        return today + timedelta(days=1)
    if re.search(r"\btoday\b", text):
        return today

    # 5) Plain weekday names: "by friday"
    for name, idx in sorted(_WEEKDAYS.items(), key=lambda kv: len(kv[0]), reverse=True):
        if re.search(rf"\b{name}\b", text):
            return _next_weekday(idx)

    return None


def _parse_tone(raw: str) -> Tone | None:
    """Match a canonical tone word OR a common synonym phrase."""
    token = raw.lower()
    for canonical in Tone:
        if re.search(rf"\b{re.escape(canonical.value)}\b", token):
            return canonical
    # Longest phrase first so "hype energy" beats "energy" etc.
    for phrase, canonical in sorted(
        TONE_SYNONYMS.items(), key=lambda kv: len(kv[0]), reverse=True
    ):
        if phrase in token:
            return canonical
    return None


def _parse_audience(raw: str) -> str | None:
    token = raw.lower()
    for needle, label in sorted(_AUDIENCE, key=lambda kv: len(kv[0]), reverse=True):
        if re.search(rf"\b{re.escape(needle)}", token):
            return label
    # Generic fallback: "targeting <free-text audience>"
    m = re.search(
        r"\btarget(?:ing|s|ed)?\s+(?:the\s+|an?\s+|for\s+)?"
        r"([a-z][a-z0-9 \-']{1,60}?)"
        r"(?=\s*(?:,|\.|$|kinda|with|and|has to|must|ready|by |for ))",
        token,
    )
    if m:
        return " ".join(word.capitalize() for word in m.group(1).split())
    return None


def _find_product(raw: str) -> str | None:
    token = raw.lower()
    for needle, label in sorted(_PRODUCTS, key=lambda kv: len(kv[0]), reverse=True):
        if needle in token:
            return label
    return None


def _campaign_name(raw: str, product_label: str | None) -> str | None:
    # Explicit naming: "name it X", "campaign called X", "campaign: X"
    patterns = [
        r"\b(?:name|call|title)\s+(?:it|the campaign|the drop)\s+([A-Za-z0-9][^.,;!?\"']{1,60}?)",
        r"\bcampaign\s+(?:called|named|titled)\s+[\"']?([A-Za-z0-9][^.,;!?\"]{1,60})",
        r"\b(?:campaign|drop|launch)\s*[:]\s*([A-Za-z0-9][^.,;!?\"]{1,60})",
    ]
    for pattern in patterns:
        m = re.search(pattern, raw, re.IGNORECASE)
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip().rstrip(": -")
            if name:
                return name
    if product_label:
        return f"{product_label} Campaign"
    return None


def _key_message(raw: str, tone: Tone | None, product_label: str | None) -> str | None:
    # Explicit "message: ..." / "key message - ..." in the brief wins.
    m = re.search(
        r"(?:key message|message|tagline)\s*[:\-]\s*[\"']?([^\"'\n]{5,300})",
        raw,
        re.IGNORECASE,
    )
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    if product_label:
        tone_key = tone or Tone.PROFESSIONAL
        template = _KEY_TEMPLATES.get(tone_key, _KEY_TEMPLATES[Tone.PROFESSIONAL])
        return template.format(p=product_label.lower())
    return None


# --------------------------------------------------------------------------- #
# Provider                                                                    #
# --------------------------------------------------------------------------- #


class LocalHeuristicProvider(LLMProvider):
    """Default provider: rule-based extraction + template-based generation."""

    name = "local"

    def parse_brief(
        self,
        raw_brief: str,
        *,
        issues: list[ValidationIssue] | None = None,
    ) -> dict[str, Any]:
        """Extract what we are confident about; leave the rest for validation.

        When ``issues`` is supplied (a repair pass), we only bother re-deriving
        the fields that were flagged as broken.
        """
        broken = {issue.field for issue in issues} if issues else None

        def _wanted(field: str) -> bool:
            return broken is None or field in broken

        product = _find_product(raw_brief)
        tone = _parse_tone(raw_brief)
        result: dict[str, Any] = {}

        if _wanted("deadline"):
            deadline = _parse_deadline(raw_brief)
            if deadline:
                result["deadline"] = deadline.isoformat()

        if _wanted("tone") and tone:
            result["tone"] = tone.value

        if _wanted("target_audience"):
            audience = _parse_audience(raw_brief)
            if audience:
                result["target_audience"] = audience

        if _wanted("campaign_name"):
            name = _campaign_name(raw_brief, product)
            if name:
                result["campaign_name"] = name

        if _wanted("key_message"):
            message = _key_message(raw_brief, tone, product)
            if message:
                result["key_message"] = message

        return result

    # ------------------------------------------------------------------ #
    # Generation (Agent 2): templates flavoured by the validated tone.   #
    # ------------------------------------------------------------------ #
    def generate_creative(self, brief: CreativeBrief) -> dict[str, Any]:
        tone = brief.tone
        style = _GEN_STYLE.get(tone, _GEN_STYLE[Tone.PROFESSIONAL])
        message = brief.key_message.rstrip(".")
        audience = brief.target_audience
        campaign = brief.campaign_name

        ad_concept = f"{message} — {audience} can't miss this one."
        social_caption = (
            f"{message}.\n\n{style['cta']}\n\n"
            f"{campaign} • made for {audience}."
        )

        return {
            "ad_concept": ad_concept,
            "social_caption": social_caption,
            "hashtags": self._hashtags(brief, style["tags"]),
        }

    @staticmethod
    def _hashtags(brief: CreativeBrief, tone_tags: list[str]) -> list[str]:
        def slug(phrase: str) -> str:
            words = re.sub(r"[^A-Za-z0-9 ]", "", phrase).split()
            return "".join(word.capitalize() for word in words)

        seen: list[str] = []

        def add(tag: str) -> None:
            tag = tag if tag.startswith("#") else f"#{tag}"
            if tag and tag not in seen:
                seen.append(tag)

        add(slug(brief.campaign_name))
        add(slug(brief.target_audience))
        add(brief.tone.value.capitalize())
        for tag in tone_tags:
            add(tag)
        return seen[:6]
