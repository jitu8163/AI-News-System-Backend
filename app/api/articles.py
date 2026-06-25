from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.article import ArticleDetailResponse, ArticleFilters, ArticleResponse
from app.schemas.common import PaginatedResponse
from app.services.article_service import ArticleService

router = APIRouter(prefix="/articles", tags=["articles"])


def _svc(session: AsyncSession = Depends(get_db)) -> ArticleService:
    return ArticleService(session)


@router.get("", response_model=PaginatedResponse[ArticleResponse])
async def list_articles(
    keyword_id: Optional[int] = Query(None),
    disease_name: Optional[str] = Query(None),
    disease_category: Optional[str] = Query(None),
    risk_level: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    svc: ArticleService = Depends(_svc),
) -> PaginatedResponse[ArticleResponse]:
    """List articles with optional filters and pagination (public)."""
    filters = ArticleFilters(
        keyword_id=keyword_id,
        disease_name=disease_name,
        disease_category=disease_category,
        risk_level=risk_level,
        country=country,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return await svc.list_articles(filters)


@router.get("/{article_id}", response_model=ArticleDetailResponse)
async def get_article(
    article_id: int,
    svc: ArticleService = Depends(_svc),
) -> ArticleDetailResponse:
    """Get a single article with full content (public)."""
    article = await svc.get_article(article_id)
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")
    return ArticleDetailResponse.model_validate(article)
