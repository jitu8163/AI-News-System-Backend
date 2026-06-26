"""State registry for India-scoped Google News collection.

This platform tracks news across the states and union territories of India.
Every region uses the Google News **India English edition** (``hl=en-IN``,
``gl=IN``, ``ceid=IN:en``); the only thing that varies per state is the search
query, which is scoped by appending the state name (e.g. ``"Dengue Kerala"``).

The special value ``ALL_INDIA`` uses the national India edition with no state
term appended to the query — i.e. pan-India coverage.

NOTE: For backward compatibility with the rest of the codebase the public
symbols keep their original names (``COUNTRIES``, ``WORLDWIDE``,
``edition_params`` …). They now describe Indian states rather than countries,
and the article ``country`` column holds the state name.
"""
from __future__ import annotations

# Pan-India option (the former "Worldwide"). Kept as ``WORLDWIDE`` so existing
# imports continue to work; the displayed/stored value is "All India".
WORLDWIDE = "All India"
ALL_INDIA = WORLDWIDE  # readable alias

# India English Google News edition shared by every state-scoped query.
_INDIA_EDITION = ("en-IN", "IN", "IN:en")

# States & union territories of India. Each maps to the shared India edition;
# they differ only by the query term appended in the collector.
_STATES: list[str] = [
    # States
    "Andhra Pradesh",
    "Arunachal Pradesh",
    "Assam",
    "Bihar",
    "Chhattisgarh",
    "Goa",
    "Gujarat",
    "Haryana",
    "Himachal Pradesh",
    "Jharkhand",
    "Karnataka",
    "Kerala",
    "Madhya Pradesh",
    "Maharashtra",
    "Manipur",
    "Meghalaya",
    "Mizoram",
    "Nagaland",
    "Odisha",
    "Punjab",
    "Rajasthan",
    "Sikkim",
    "Tamil Nadu",
    "Telangana",
    "Tripura",
    "Uttar Pradesh",
    "Uttarakhand",
    "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands",
    "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu",
    "Delhi",
    "Jammu and Kashmir",
    "Ladakh",
    "Lakshadweep",
    "Puducherry",
]

# name -> (hl, gl, ceid). Every state shares the India edition.
COUNTRIES: dict[str, tuple[str, str, str]] = {name: _INDIA_EDITION for name in _STATES}

# Pan-India national edition for the "All India" option.
_WORLDWIDE_EDITION = _INDIA_EDITION

# All selectable region values: All India first, then states alphabetically.
AVAILABLE_REGIONS: list[str] = [WORLDWIDE, *sorted(COUNTRIES.keys())]


def is_valid_region(name: str) -> bool:
    return name == WORLDWIDE or name in COUNTRIES


def edition_params(country: str | None) -> tuple[str, str, str]:
    """Return (hl, gl, ceid). Always the India edition (national or state-scoped)."""
    if not country or country == WORLDWIDE:
        return _WORLDWIDE_EDITION
    return COUNTRIES.get(country, _WORLDWIDE_EDITION)


def normalize_regions(regions: list[str] | None) -> list[str]:
    """Keep only valid regions; default to all states. 'All India' is exclusive."""
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
