from datetime import datetime

from sqlalchemy import func, select, distinct, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.article import Article, ArticleKeyword, NUMERIC_METRICS
from app.models.keyword import Keyword
from app.repositories.base import BaseRepository


def _metric_sums() -> list:
    """SELECT expressions: SUM(metric) coalesced to 0, one per numeric metric."""
    return [func.coalesce(func.sum(getattr(Article, k)), 0).label(k) for k in NUMERIC_METRICS]


def _has_any_metric():
    """True for articles that report at least one numeric impact metric."""
    return or_(*[getattr(Article, k).isnot(None) for k in NUMERIC_METRICS])


def _valid_country():
    return (
        Article.country.isnot(None),
        Article.country != "",
        func.lower(Article.country) != "null",
    )


class ArticleRepository(BaseRepository[Article]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Article, session)

    async def get_by_hash(self, content_hash: str) -> Article | None:
        result = await self._session.execute(
            select(Article).where(Article.content_hash == content_hash)
        )
        return result.scalar_one_or_none()

    async def list_filtered(
        self,
        keyword_id: int | None = None,
        disease_name: str | None = None,
        disease_category: str | None = None,
        risk_level: str | None = None,
        country: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Article], int]:
        query = select(Article)

        if keyword_id is not None:
            query = query.join(
                ArticleKeyword, ArticleKeyword.article_id == Article.id
            ).where(ArticleKeyword.keyword_id == keyword_id)

        if disease_name:
            query = query.where(Article.disease_name == disease_name)
        if disease_category:
            query = query.where(Article.disease_category == disease_category)
        if risk_level:
            query = query.where(Article.risk_level == risk_level)
        if country:
            query = query.where(Article.country == country)
        if date_from:
            query = query.where(Article.published_date >= date_from)
        if date_to:
            query = query.where(Article.published_date <= date_to)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self._session.execute(count_query)).scalar_one()

        # Newest published first; articles with no publish date fall back to
        # scrape time so they still sort sensibly, never above dated articles.
        query = (
            query.order_by(
                Article.published_date.desc().nullslast(),
                Article.created_at.desc(),
            )
            .offset(offset)
            .limit(limit)
        )
        items = list((await self._session.execute(query)).scalars().all())

        return items, total

    # --- simple group-by counts ---

    async def count_by_disease(self, limit: int = 20) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(Article.disease_name, func.count(Article.id))
            .where(Article.disease_name.isnot(None))
            .group_by(Article.disease_name)
            .order_by(func.count(Article.id).desc())
            .limit(limit)
        )
        return result.all()

    async def count_by_category(self) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(Article.disease_category, func.count(Article.id))
            .where(Article.disease_category.isnot(None))
            .group_by(Article.disease_category)
            .order_by(func.count(Article.id).desc())
        )
        return result.all()

    async def count_by_risk(self) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(Article.risk_level, func.count(Article.id))
            .where(Article.risk_level.isnot(None))
            .group_by(Article.risk_level)
        )
        return result.all()

    async def keyword_article_counts(self) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(Keyword.term, func.count(distinct(ArticleKeyword.article_id)))
            .join(ArticleKeyword, ArticleKeyword.keyword_id == Keyword.id)
            .group_by(Keyword.term)
            .order_by(func.count(distinct(ArticleKeyword.article_id)).desc())
            .limit(10)
        )
        return result.all()

    async def daily_counts(self, days: int = 30) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(
                func.date(Article.created_at).label("date"),
                func.count(Article.id).label("count"),
            )
            .group_by(func.date(Article.created_at))
            .order_by(func.date(Article.created_at))
            .limit(days)
        )
        return result.all()

    async def country_counts_all(self) -> list[tuple[str, int]]:
        """Article counts for every country (no top-N limit)."""
        result = await self._session.execute(
            select(Article.country, func.count(Article.id))
            .where(*_valid_country())
            .group_by(Article.country)
            .order_by(func.count(Article.id).desc())
        )
        return result.all()

    async def count_by_country(self) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(Article.country, func.count(Article.id))
            .where(*_valid_country())
            .group_by(Article.country)
            .order_by(func.count(Article.id).desc())
            .limit(20)
        )
        return result.all()

    # --- impact metric aggregations (death/positive/suspected) ---

    async def counts_totals(self) -> dict[str, int]:
        """Sum each numeric impact metric across all articles."""
        row = (await self._session.execute(select(*_metric_sums()))).one()
        return {k: int(v) for k, v in zip(NUMERIC_METRICS, row)}

    async def impact_filtered(
        self,
        keyword_id: int | None = None,
        country: str | None = None,
    ) -> tuple[dict[str, int], list[tuple[str, dict[str, int]]]]:
        """Return (totals, daily_timeline) of impact metrics for a filtered subset."""
        date_col = func.date(Article.created_at)
        query = select(date_col, *_metric_sums()).where(_has_any_metric())
        if keyword_id is not None:
            query = query.join(
                ArticleKeyword, ArticleKeyword.article_id == Article.id
            ).where(ArticleKeyword.keyword_id == keyword_id)
        if country:
            query = query.where(Article.country == country)
        query = query.group_by(date_col).order_by(date_col)

        totals = {k: 0 for k in NUMERIC_METRICS}
        daily: list[tuple[str, dict[str, int]]] = []
        for row in (await self._session.execute(query)).all():
            metrics = {k: int(v) for k, v in zip(NUMERIC_METRICS, row[1:])}
            for k in NUMERIC_METRICS:
                totals[k] += metrics[k]
            daily.append((str(row[0]), metrics))
        return totals, daily

    async def counts_by_disease(
        self,
        limit: int = 10,
        country: str | None = None,
    ) -> list[tuple[str, dict[str, int]]]:
        """Sum impact metrics per disease. Skips all-zero diseases."""
        query = (
            select(Article.disease_name, *_metric_sums())
            .where(Article.disease_name.isnot(None))
            .where(_has_any_metric())
        )
        if country:
            query = query.where(Article.country == country)
        query = query.group_by(Article.disease_name)

        items: list[tuple[str, dict[str, int]]] = []
        for row in (await self._session.execute(query)).all():
            metrics = {k: int(v) for k, v in zip(NUMERIC_METRICS, row[1:])}
            if sum(metrics.values()) > 0:
                items.append((row[0], metrics))
        items.sort(key=lambda kv: sum(kv[1].values()), reverse=True)
        return items[:limit]

    async def counts_timeline(self) -> list[tuple[str, dict[str, int]]]:
        """Sum impact metrics per day (by article creation date), oldest first."""
        date_col = func.date(Article.created_at)
        result = await self._session.execute(
            select(date_col, *_metric_sums())
            .where(_has_any_metric())
            .group_by(date_col)
            .order_by(date_col)
        )
        return [
            (str(row[0]), {k: int(v) for k, v in zip(NUMERIC_METRICS, row[1:])})
            for row in result.all()
        ]

    async def list_recent(self, limit: int = 10) -> list[Article]:
        result = await self._session.execute(
            select(Article)
            .order_by(
                Article.published_date.desc().nullslast(),
                Article.created_at.desc(),
            )
            .limit(limit)
        )
        return list(result.scalars().all())

    async def list_unprocessed(self, limit: int = 50) -> list[Article]:
        result = await self._session.execute(
            select(Article)
            .where(Article.ai_processed.is_(False))
            .where(Article.extraction_failed.is_(False))
            .order_by(Article.created_at)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update(self, article: Article, **kwargs) -> Article:
        for key, value in kwargs.items():
            setattr(article, key, value)
        await self._session.flush()
        await self._session.refresh(article)
        return article
