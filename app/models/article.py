from datetime import date, datetime, timezone
from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# Numeric casualty/impact metrics extracted per article (One Health model).
NUMERIC_METRICS = ("death_count", "positive_cases", "suspected_cases")

# Risk level values the AI may assign.
RISK_LEVELS = ("High", "Medium", "Low")


class Article(Base):
    """A news article plus the structured "One Health" facts extracted from it.

    Source/operational columns (title, url, hash, timestamps, processing flags)
    support collection and dedup; the remaining columns hold the structured
    information the AI extracts per the client's target schema.
    """

    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    # --- Source / operational ---
    title: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    rss_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    article_url: Mapped[str] = mapped_column(Text, nullable=False)
    source_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    ai_processed: Mapped[bool] = mapped_column(default=False, nullable=False)
    extraction_failed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # --- Structured extraction (One Health schema) ---
    disease_name: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    disease_category: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    human_health_impact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    animal_health_impact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    environmental_health_impact: Mapped[str | None] = mapped_column(String(255), nullable=True)
    symptoms: Mapped[str | None] = mapped_column(Text, nullable=True)
    death_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    positive_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    suspected_cases: Mapped[int | None] = mapped_column(Integer, nullable=True)
    species_affected: Mapped[str | None] = mapped_column(String(255), nullable=True)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    environmental_factors: Mapped[str | None] = mapped_column(String(500), nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    event_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Timestamps ---
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    article_keywords: Mapped[list["ArticleKeyword"]] = relationship(  # noqa: F821
        back_populates="article", cascade="all, delete-orphan"
    )


class ArticleKeyword(Base):
    __tablename__ = "article_keywords"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False, index=True
    )
    keyword_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("keywords.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    article: Mapped["Article"] = relationship(back_populates="article_keywords")
    keyword: Mapped["Keyword"] = relationship(back_populates="article_keywords")  # noqa: F821
