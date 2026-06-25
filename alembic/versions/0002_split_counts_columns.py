"""split article counts JSON into separate metric columns

Replaces the single ``counts`` JSON column on ``articles`` with one integer
column per metric (killed, injured, affected, arrested, cases, recovered),
backfilling existing values before dropping the JSON column.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-25
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

METRICS = ("killed", "injured", "affected", "arrested", "cases", "recovered")


def upgrade() -> None:
    for metric in METRICS:
        op.add_column("articles", sa.Column(metric, sa.Integer(), nullable=True))

    # Backfill from the existing JSON column. ``->>`` yields text; cast to int.
    # Non-numeric / missing keys become NULL.
    set_clause = ", ".join(
        f"{m} = NULLIF(counts->>'{m}', '')::int" for m in METRICS
    )
    op.execute(f"UPDATE articles SET {set_clause} WHERE counts IS NOT NULL")

    op.drop_column("articles", "counts")


def downgrade() -> None:
    op.add_column(
        "articles",
        sa.Column("counts", sa.JSON(), nullable=True),
    )

    # Rebuild the JSON object from the per-metric columns, keeping only non-null
    # entries (jsonb_strip_nulls drops keys whose value is null).
    pairs = ", ".join(f"'{m}', {m}" for m in METRICS)
    op.execute(
        f"UPDATE articles "
        f"SET counts = jsonb_strip_nulls(jsonb_build_object({pairs})) "
        f"WHERE {' OR '.join(f'{m} IS NOT NULL' for m in METRICS)}"
    )

    for metric in METRICS:
        op.drop_column("articles", metric)
