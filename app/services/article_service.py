from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article
from app.repositories.article_repository import ArticleRepository
from app.schemas.article import ArticleFilters
from app.schemas.common import PaginatedResponse
from app.schemas.article import ArticleResponse
import math


class ArticleService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = ArticleRepository(session)

    async def list_articles(
        self, filters: ArticleFilters
    ) -> PaginatedResponse[ArticleResponse]:
        offset = (filters.page - 1) * filters.page_size
        items, total = await self._repo.list_filtered(
            keyword_id=filters.keyword_id,
            disease_name=filters.disease_name,
            disease_category=filters.disease_category,
            risk_level=filters.risk_level,
            country=filters.country,
            date_from=filters.date_from,
            date_to=filters.date_to,
            offset=offset,
            limit=filters.page_size,
        )
        return PaginatedResponse(
            items=[ArticleResponse.model_validate(a) for a in items],
            total=total,
            page=filters.page,
            page_size=filters.page_size,
            total_pages=max(1, math.ceil(total / filters.page_size)),
        )

    async def get_article(self, article_id: int) -> Article | None:
        return await self._repo.get(article_id)
