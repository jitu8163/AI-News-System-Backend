from __future__ import annotations

import json
import re
from datetime import date

from groq import AsyncGroq
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings
from app.models.article import RISK_LEVELS
from app.utils.logging import get_logger

logger = get_logger(__name__)

_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

_MAX_CHARS = 4000
# If content is shorter than this, treat it as headline-only (RSS fallback)
_MIN_BODY_LEN = 200

# Greedy match so nested objects are captured in full
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_DATE_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

# Text fields returned verbatim (after null-cleaning); the rest are typed below.
_TEXT_FIELDS = (
    "disease_name",
    "disease_category",
    "human_health_impact",
    "animal_health_impact",
    "environmental_health_impact",
    "symptoms",
    "species_affected",
    "country",
    "environmental_factors",
    "ai_summary",
)
_INT_FIELDS = ("death_count", "positive_cases", "suspected_cases")

# The full set of keys the extractor returns.
EXTRACTION_KEYS = _TEXT_FIELDS + _INT_FIELDS + ("risk_level", "event_date")


def _empty_result() -> dict:
    return {k: None for k in EXTRACTION_KEYS}


def _clean_text(v) -> str | None:
    if not isinstance(v, str):
        return None
    v = v.strip()
    if not v or v.lower() in ("null", "none", "n/a", "not mentioned", "unknown", "not specified"):
        return None
    return v


def _clean_int(v) -> int | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int):
        return v if v > 0 else None
    if isinstance(v, str):
        m = re.search(r"\d[\d,]*", v)
        if m:
            try:
                n = int(m.group().replace(",", ""))
                return n if n > 0 else None
            except ValueError:
                return None
    return None


def _clean_risk(v) -> str | None:
    if not isinstance(v, str):
        return None
    v = v.strip().lower()
    for level in RISK_LEVELS:
        if level.lower() in v:
            return level
    return None


def _clean_date(v) -> date | None:
    if not isinstance(v, str):
        return None
    m = _DATE_RE.search(v)
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


@retry(
    retry=retry_if_exception_type(Exception),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
async def _chat(prompt: str, max_tokens: int = 900) -> str:
    response = await _client.chat.completions.create(
        model=settings.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def _build_prompt(title: str, content: str, keyword_hint: str | None) -> str:
    has_body = len(content.strip()) >= _MIN_BODY_LEN
    sample = content[:_MAX_CHARS]

    if has_body:
        context = f"Title: {title}\n\nArticle content:\n{sample}"
        summary_instruction = (
            "Write a detailed 4-6 sentence factual summary of this article covering "
            "the disease/outbreak, location, who/what is affected, reported numbers, and implications."
        )
    else:
        context = f"Headline: {title}"
        summary_instruction = (
            "Based on this headline, write a detailed 4-6 sentence informative summary explaining "
            "what this story is likely about, including relevant background and likely implications. "
            "Write the summary directly — do not say you lack the article."
        )

    hint = f'\nThe article was matched on the search term "{keyword_hint}".' if keyword_hint else ""

    return f"""You are a One Health news analyst covering India. Extract structured outbreak/disease information from the news item below, paying attention to which Indian state or union territory it concerns.{hint}

{summary_instruction}

Extract these fields. Carefully scan the text for cities, regions, governments, datelines, numbers, symptoms, animals, and environmental causes.
- disease_name: the specific disease/condition the article is about (e.g. "Leptospirosis", "H5N1 Bird Flu"). Null if none.
- disease_category: classify the disease, e.g. "Bacterial Disease", "Viral Disease", "Parasitic Disease", "Fungal Disease", "Zoonotic Disease", "Vector-borne Disease". Null if unclear.
- human_health_impact: does it affect humans? "Yes", "No", or a short phrase. Null if unknown.
- animal_health_impact: animal involvement, e.g. "Rodent Related", "Poultry", "Cattle", "No". Null if none.
- environmental_health_impact: environmental angle, e.g. "Flooding / Waterlogging", "Contaminated Water". Null if none.
- symptoms: symptoms mentioned, comma-separated. Null if not mentioned.
- death_count: integer number of deaths/fatalities. Null if not stated.
- positive_cases: integer number of confirmed/positive cases. Null if not stated.
- suspected_cases: integer number of suspected/probable cases. Null if not stated.
- species_affected: affected species, comma-separated (e.g. "Humans, Rodents"). Null if none.
- country: the Indian state or union territory the article is primarily about (e.g. "Maharashtra", "Kerala", "Delhi"). Use the full official state name. If only a city is mentioned, return the state it belongs to (e.g. Mumbai -> "Maharashtra", Bengaluru -> "Karnataka"). Null if no Indian location is referenced.
- environmental_factors: contributing environmental conditions, e.g. "Flooding, Waterlogging". Null if none.
- risk_level: overall public-health risk — exactly one of "High", "Medium", "Low" based on severity, spread, and fatalities.
- event_date: the date the event/outbreak occurred or was reported, as "YYYY-MM-DD". Null if not determinable.
- ai_summary: the summary described above.

{context}

Respond ONLY with this exact JSON (no extra text), using null where unknown:
{{"disease_name": null, "disease_category": null, "human_health_impact": null, "animal_health_impact": null, "environmental_health_impact": null, "symptoms": null, "death_count": null, "positive_cases": null, "suspected_cases": null, "species_affected": null, "country": null, "environmental_factors": null, "risk_level": null, "event_date": null, "ai_summary": "..."}}"""


async def process_article(
    title: str, content: str, keyword_hint: str | None = None
) -> dict:
    """Run a single Groq call and return the structured One Health fields.

    Values are typed/cleaned: text fields are null-cleaned strings, the three
    count fields are positive ints or None, ``risk_level`` is one of
    ``RISK_LEVELS``, and ``event_date`` is a ``date`` or None.
    """
    prompt = _build_prompt(title, content, keyword_hint)
    raw = await _chat(prompt)

    result = _empty_result()
    try:
        match = _JSON_RE.search(raw)
        data = json.loads(match.group() if match else raw)
    except (json.JSONDecodeError, AttributeError):
        logger.warning("json_parse_failed", raw=raw[:120])
        # Fall back to using the raw text as the summary so the article isn't lost.
        result["ai_summary"] = raw[:600] if len(raw) > 20 else title
        return result

    for k in _TEXT_FIELDS:
        result[k] = _clean_text(data.get(k))
    for k in _INT_FIELDS:
        result[k] = _clean_int(data.get(k))
    result["risk_level"] = _clean_risk(data.get("risk_level"))
    result["event_date"] = _clean_date(data.get("event_date"))

    # Prefer the matched keyword as the disease name when the model didn't name one.
    if not result["disease_name"] and keyword_hint:
        result["disease_name"] = keyword_hint

    logger.info(
        "ai_processed",
        disease=result["disease_name"],
        country=result["country"],
        risk=result["risk_level"],
        deaths=result["death_count"],
    )
    return result
