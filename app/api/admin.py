from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.collectors.countries import AVAILABLE_REGIONS
from app.core.database import get_db
from app.models.article import Article, ArticleKeyword
from app.models.user import User
from app.scheduler.scheduler import VALID_INTERVALS, collect_and_process, get_interval_hours, update_interval
from app.services.settings_store import get_monitored_countries, set_monitored_countries
from app.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/fetch-now", status_code=202)
async def fetch_now(
    background_tasks: BackgroundTasks,
    _: User = Depends(get_current_admin),
):
    """Trigger an immediate news collection run (admin only)."""
    background_tasks.add_task(collect_and_process)
    return {"message": "News collection started"}


class SchedulerIntervalResponse(BaseModel):
    interval_hours: float
    valid_options: list[float]


class SchedulerIntervalRequest(BaseModel):
    interval_hours: float


@router.get("/scheduler-interval", response_model=SchedulerIntervalResponse)
async def get_scheduler_interval(_: User = Depends(get_current_admin)):
    """Return current scheduler fetch interval."""
    return SchedulerIntervalResponse(interval_hours=get_interval_hours(), valid_options=VALID_INTERVALS)


@router.put("/scheduler-interval", response_model=SchedulerIntervalResponse)
async def set_scheduler_interval(
    body: SchedulerIntervalRequest,
    _: User = Depends(get_current_admin),
):
    """Update scheduler fetch interval."""
    if body.interval_hours not in VALID_INTERVALS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"interval_hours must be one of {VALID_INTERVALS}",
        )
    update_interval(body.interval_hours)
    return SchedulerIntervalResponse(interval_hours=body.interval_hours, valid_options=VALID_INTERVALS)


class CountriesResponse(BaseModel):
    selected: list[str]
    available: list[str]


class CountriesRequest(BaseModel):
    countries: list[str]


@router.get("/countries", response_model=CountriesResponse)
async def get_countries(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Return the currently monitored regions and all selectable options."""
    selected = await get_monitored_countries(session)
    return CountriesResponse(selected=selected, available=AVAILABLE_REGIONS)


@router.put("/countries", response_model=CountriesResponse)
async def set_countries(
    body: CountriesRequest,
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Update the monitored regions. 'Worldwide' is exclusive; invalid names are dropped."""
    selected = await set_monitored_countries(session, body.countries)
    return CountriesResponse(selected=selected, available=AVAILABLE_REGIONS)


@router.delete("/articles", status_code=200)
async def delete_all_articles(
    _: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_db),
):
    """Delete all articles and their keyword links."""
    await session.execute(delete(ArticleKeyword))
    result = await session.execute(delete(Article))
    deleted = result.rowcount
    logger.info("all_articles_deleted", count=deleted)
    return {"deleted": deleted}
