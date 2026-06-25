from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.dashboard import DashboardStats, ImpactStats, CountryCount
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    session: AsyncSession = Depends(get_db),
) -> DashboardStats:
    """Return aggregated analytics for the dashboard (public)."""
    svc = DashboardService(session)
    return await svc.get_stats()


@router.get("/impact", response_model=ImpactStats)
async def get_impact(
    keyword_id: Optional[int] = Query(None),
    country: Optional[str] = Query(None),
    session: AsyncSession = Depends(get_db),
) -> ImpactStats:
    """Return health-impact totals/timeline/by-disease, optionally filtered (public)."""
    svc = DashboardService(session)
    return await svc.get_impact(keyword_id=keyword_id, country=country)


@router.get("/country-counts", response_model=list[CountryCount])
async def get_country_counts(
    session: AsyncSession = Depends(get_db),
) -> list[CountryCount]:
    """Return article counts for every country (no top-N limit) for filters and analytics."""
    svc = DashboardService(session)
    return await svc.get_country_counts()
