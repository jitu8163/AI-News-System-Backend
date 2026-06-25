from datetime import datetime

from pydantic import BaseModel


class DiseaseCount(BaseModel):
    disease: str
    count: int


class CategoryCount(BaseModel):
    category: str
    count: int


class RiskCount(BaseModel):
    risk_level: str
    count: int


class KeywordStat(BaseModel):
    keyword: str
    count: int


class DailyCount(BaseModel):
    date: str
    count: int


class CountryCount(BaseModel):
    country: str
    count: int


class DiseaseImpact(BaseModel):
    """Aggregated casualty/impact counts for one disease."""
    disease: str
    death_count: int = 0
    positive_cases: int = 0
    suspected_cases: int = 0
    total: int = 0


class ImpactTimelinePoint(BaseModel):
    date: str
    death_count: int = 0
    positive_cases: int = 0
    suspected_cases: int = 0


class RecentArticleItem(BaseModel):
    id: int
    title: str
    disease_name: str | None
    disease_category: str | None
    risk_level: str | None
    country: str | None
    source_name: str | None
    published_date: datetime | None
    article_url: str

    model_config = {"from_attributes": True}


class ImpactStats(BaseModel):
    """Filterable health-impact aggregates for the dashboard."""
    totals: dict[str, int]
    timeline: list[ImpactTimelinePoint]
    by_disease: list[DiseaseImpact]


class DashboardStats(BaseModel):
    total_articles: int
    articles_by_disease: list[DiseaseCount]
    articles_by_category: list[CategoryCount]
    risk_distribution: list[RiskCount]
    keyword_stats: list[KeywordStat]
    daily_trend: list[DailyCount]
    total_keywords: int
    active_keywords: int
    articles_by_country: list[CountryCount]
    impact_totals: dict[str, int]
    impact_by_disease: list[DiseaseImpact]
    impact_timeline: list[ImpactTimelinePoint]
    recent_articles: list[RecentArticleItem]
