"""Country registry for region-scoped Google News collection.

Each entry maps a display name to the Google News edition parameters
(`hl` language, `gl` geo, `ceid` country:lang) used to build an RSS query
scoped to that country. Every edition requests the English (`:en`) feed so
summaries stay in English regardless of the country's primary language.

The special value ``WORLDWIDE`` uses the global English edition with no
country term appended to the query.
"""
from __future__ import annotations

WORLDWIDE = "Worldwide"

# name -> ISO country code. All editions are requested in English (en / XX:en).
# Broad coverage across every continent using Google News country editions
# that return usable English-language results.
_COUNTRY_CODES: dict[str, str] = {
    # North America
    "United States": "US",
    "Canada": "CA",
    "Mexico": "MX",
    "Cuba": "CU",
    # South America
    "Brazil": "BR",
    "Argentina": "AR",
    "Colombia": "CO",
    "Chile": "CL",
    "Peru": "PE",
    "Venezuela": "VE",
    # Europe
    "United Kingdom": "GB",
    "Ireland": "IE",
    "Germany": "DE",
    "France": "FR",
    "Italy": "IT",
    "Spain": "ES",
    "Portugal": "PT",
    "Netherlands": "NL",
    "Belgium": "BE",
    "Switzerland": "CH",
    "Austria": "AT",
    "Sweden": "SE",
    "Norway": "NO",
    "Denmark": "DK",
    "Finland": "FI",
    "Poland": "PL",
    "Czechia": "CZ",
    "Hungary": "HU",
    "Romania": "RO",
    "Greece": "GR",
    "Ukraine": "UA",
    "Russia": "RU",
    # Middle East
    "Turkey": "TR",
    "Israel": "IL",
    "United Arab Emirates": "AE",
    "Saudi Arabia": "SA",
    "Qatar": "QA",
    "Kuwait": "KW",
    "Bahrain": "BH",
    "Oman": "OM",
    "Lebanon": "LB",
    "Jordan": "JO",
    # Africa
    "Egypt": "EG",
    "Morocco": "MA",
    "Nigeria": "NG",
    "Kenya": "KE",
    "Ghana": "GH",
    "Uganda": "UG",
    "Tanzania": "TZ",
    "Ethiopia": "ET",
    "Zimbabwe": "ZW",
    "South Africa": "ZA",
    "Botswana": "BW",
    "Namibia": "NA",
    # South Asia
    "India": "IN",
    "Pakistan": "PK",
    "Bangladesh": "BD",
    "Sri Lanka": "LK",
    "Nepal": "NP",
    # South-East & East Asia
    "Singapore": "SG",
    "Malaysia": "MY",
    "Philippines": "PH",
    "Indonesia": "ID",
    "Thailand": "TH",
    "Vietnam": "VN",
    "Hong Kong": "HK",
    "Taiwan": "TW",
    "Japan": "JP",
    "South Korea": "KR",
    "China": "CN",
    # Oceania
    "Australia": "AU",
    "New Zealand": "NZ",
}

# name -> (hl, gl, ceid)
COUNTRIES: dict[str, tuple[str, str, str]] = {
    name: (f"en-{code}", code, f"{code}:en") for name, code in _COUNTRY_CODES.items()
}

# Global English edition for the "Worldwide" option.
_WORLDWIDE_EDITION = ("en-US", "US", "US:en")

# All selectable region values: Worldwide first, then countries alphabetically.
AVAILABLE_REGIONS: list[str] = [WORLDWIDE, *sorted(COUNTRIES.keys())]


def is_valid_region(name: str) -> bool:
    return name == WORLDWIDE or name in COUNTRIES


def edition_params(country: str | None) -> tuple[str, str, str]:
    """Return (hl, gl, ceid) for a country, or the global edition for Worldwide/None."""
    if not country or country == WORLDWIDE:
        return _WORLDWIDE_EDITION
    return COUNTRIES.get(country, _WORLDWIDE_EDITION)


def normalize_regions(regions: list[str] | None) -> list[str]:
    """Keep only valid regions; default to all available countries. Worldwide is exclusive."""
    if not regions:
        return list(COUNTRIES.keys())
    valid = [r for r in regions if is_valid_region(r)]
    if not valid:
        return list(COUNTRIES.keys())
    if WORLDWIDE in valid:
        return [WORLDWIDE]
    # de-duplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for r in valid:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return out
