"""Persisted runtime settings backed by the app_settings key/value table."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.countries import normalize_regions
from app.models.app_setting import AppSetting

_MONITORED_COUNTRIES_KEY = "monitored_countries"


async def get_monitored_countries(session: AsyncSession) -> list[str]:
    """Return the list of regions to collect news for. Defaults to all available countries."""
    result = await session.execute(
        select(AppSetting).where(AppSetting.key == _MONITORED_COUNTRIES_KEY)
    )
    row = result.scalar_one_or_none()
    value = row.value if row else None
    if not isinstance(value, list):
        value = None
    return normalize_regions(value)


async def set_monitored_countries(session: AsyncSession, regions: list[str]) -> list[str]:
    """Persist the monitored regions, returning the normalized stored value."""
    normalized = normalize_regions(regions)
    result = await session.execute(
        select(AppSetting).where(AppSetting.key == _MONITORED_COUNTRIES_KEY)
    )
    row = result.scalar_one_or_none()
    if row is None:
        session.add(AppSetting(key=_MONITORED_COUNTRIES_KEY, value=normalized))
    else:
        row.value = normalized
    await session.commit()
    return normalized
