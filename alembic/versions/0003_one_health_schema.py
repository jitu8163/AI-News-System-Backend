"""rebuild articles table around the One Health extraction schema

Drops the previous articles table (and its keyword link) and recreates them with
the structured One Health fields: disease_name, disease_category, the three
health-impact flags, symptoms, death/positive/suspected counts, species, country,
environmental factors, risk level, event date, and AI summary.

This is a destructive redesign — existing article rows are discarded.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("article_keywords")
    op.drop_table("articles")

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        # Source / operational
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("rss_summary", sa.Text(), nullable=True),
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("ai_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_failed", sa.Boolean(), nullable=False, server_default="false"),
        # Structured One Health extraction
        sa.Column("disease_name", sa.String(255), nullable=True, index=True),
        sa.Column("disease_category", sa.String(100), nullable=True, index=True),
        sa.Column("human_health_impact", sa.String(255), nullable=True),
        sa.Column("animal_health_impact", sa.String(255), nullable=True),
        sa.Column("environmental_health_impact", sa.String(255), nullable=True),
        sa.Column("symptoms", sa.Text(), nullable=True),
        sa.Column("death_count", sa.Integer(), nullable=True),
        sa.Column("positive_cases", sa.Integer(), nullable=True),
        sa.Column("suspected_cases", sa.Integer(), nullable=True),
        sa.Column("species_affected", sa.String(255), nullable=True),
        sa.Column("country", sa.String(100), nullable=True, index=True),
        sa.Column("environmental_factors", sa.String(500), nullable=True),
        sa.Column("risk_level", sa.String(20), nullable=True, index=True),
        sa.Column("event_date", sa.Date(), nullable=True),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        # Timestamps
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "article_keywords",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "keyword_id",
            sa.Integer(),
            sa.ForeignKey("keywords.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    """Recreate the previous (post-0002) articles schema. Data is not restored."""
    op.drop_table("article_keywords")
    op.drop_table("articles")

    op.create_table(
        "articles",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("rss_summary", sa.Text(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(100), nullable=True, index=True),
        sa.Column("sentiment", sa.String(50), nullable=True, index=True),
        sa.Column("country", sa.String(100), nullable=True, index=True),
        sa.Column("killed", sa.Integer(), nullable=True),
        sa.Column("injured", sa.Integer(), nullable=True),
        sa.Column("affected", sa.Integer(), nullable=True),
        sa.Column("arrested", sa.Integer(), nullable=True),
        sa.Column("cases", sa.Integer(), nullable=True),
        sa.Column("recovered", sa.Integer(), nullable=True),
        sa.Column("article_url", sa.Text(), nullable=False),
        sa.Column("source_name", sa.String(255), nullable=True),
        sa.Column("published_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=False, unique=True, index=True),
        sa.Column("ai_processed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("extraction_failed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "article_keywords",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column(
            "article_id",
            sa.Integer(),
            sa.ForeignKey("articles.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "keyword_id",
            sa.Integer(),
            sa.ForeignKey("keywords.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
