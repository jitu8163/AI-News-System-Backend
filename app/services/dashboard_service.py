from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.article_repository import ArticleRepository
from app.repositories.keyword_repository import KeywordRepository
from app.schemas.dashboard import (
    CategoryCount,
    CountryCount,
    DailyCount,
    DashboardStats,
    DiseaseCount,
    DiseaseImpact,
    ImpactStats,
    ImpactTimelinePoint,
    KeywordStat,
    RecentArticleItem,
    RiskCount,
)


class DashboardService:
    def __init__(self, session: AsyncSession) -> None:
        self._articles = ArticleRepository(session)
        self._keywords = KeywordRepository(session)

    async def get_country_counts(self) -> list[CountryCount]:
        rows = await self._articles.country_counts_all()
        return [CountryCount(country=c, count=n) for c, n in rows]

    async def get_impact(
        self,
        keyword_id: int | None = None,
        country: str | None = None,
    ) -> ImpactStats:
        totals, timeline = await self._articles.impact_filtered(keyword_id, country)
        by_disease = await self._articles.counts_by_disease(country=country)
        return ImpactStats(
            totals=totals,
            timeline=[ImpactTimelinePoint(date=d, **m) for d, m in timeline],
            by_disease=[
                DiseaseImpact(disease=t, total=sum(m.values()), **m) for t, m in by_disease
            ],
        )

    async def get_stats(self) -> DashboardStats:
        total_articles = await self._articles.count()
        by_disease = await self._articles.count_by_disease()
        by_category = await self._articles.count_by_category()
        by_risk = await self._articles.count_by_risk()
        kw_counts = await self._articles.keyword_article_counts()
        daily = await self._articles.daily_counts()
        total_kw = await self._keywords.count()
        active_kw = len(await self._keywords.list_active())
        by_country = await self._articles.count_by_country()
        impact_totals = await self._articles.counts_totals()
        impact_by_disease = await self._articles.counts_by_disease()
        impact_timeline = await self._articles.counts_timeline()
        recent = await self._articles.list_recent(10)

        return DashboardStats(
            total_articles=total_articles,
            articles_by_disease=[DiseaseCount(disease=d, count=n) for d, n in by_disease],
            articles_by_category=[CategoryCount(category=c, count=n) for c, n in by_category],
            risk_distribution=[RiskCount(risk_level=r, count=n) for r, n in by_risk],
            keyword_stats=[KeywordStat(keyword=k, count=n) for k, n in kw_counts],
            daily_trend=[DailyCount(date=str(d), count=n) for d, n in daily],
            total_keywords=total_kw,
            active_keywords=active_kw,
            articles_by_country=[CountryCount(country=c, count=n) for c, n in by_country],
            impact_totals=impact_totals,
            impact_by_disease=[
                DiseaseImpact(disease=disease, total=sum(metrics.values()), **metrics)
                for disease, metrics in impact_by_disease
            ],
            impact_timeline=[
                ImpactTimelinePoint(date=date, **metrics)
                for date, metrics in impact_timeline
            ],
            recent_articles=[RecentArticleItem.model_validate(a) for a in recent],
        )
