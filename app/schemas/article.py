from datetime import date, datetime
from pydantic import BaseModel


class ArticleResponse(BaseModel):
    id: int
    title: str
    # Structured One Health extraction
    disease_name: str | None
    disease_category: str | None
    human_health_impact: str | None
    animal_health_impact: str | None
    environmental_health_impact: str | None
    symptoms: str | None
    death_count: int | None
    positive_cases: int | None
    suspected_cases: int | None
    species_affected: str | None
    country: str | None
    environmental_factors: str | None
    risk_level: str | None
    event_date: date | None
    ai_summary: str | None
    # Source metadata
    article_url: str
    source_name: str | None
    published_date: datetime | None
    ai_processed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ArticleDetailResponse(ArticleResponse):
    content: str | None
    rss_summary: str | None


class ArticleFilters(BaseModel):
    keyword_id: int | None = None
    disease_name: str | None = None
    disease_category: str | None = None
    risk_level: str | None = None
    country: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = 1
    page_size: int = 20
