"""
Seed the initial set of monitored keywords (diseases / health topics).

Run from the backend directory:
    uv run python seed_keywords.py                 # seed the default set below
    uv run python seed_keywords.py nipah "bird flu"  # also add custom terms

Idempotent: terms that already exist are left untouched, so this is safe to
re-run. New terms are added as active. Requires the DB schema to exist first
(`alembic upgrade head`).
"""
import asyncio
import sys

from app.core.database import AsyncSessionLocal
from app.models.keyword import Keyword
from app.repositories.keyword_repository import KeywordRepository

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Default One-Health surveillance terms (human + zoonotic diseases), worldwide.
DEFAULT_KEYWORDS = [
    "dengue",
    "malaria",
    "chikungunya",
    "cholera",
    "typhoid",
    "influenza",
    "H3N2",
    "bird flu",
    "swine flu",
    "covid-19",
    "nipah virus",
    "zika virus",
    "tuberculosis",
    "measles",
    "japanese encephalitis",
    "leptospirosis",
    "hepatitis",
    "diphtheria",
    "rabies",
    "anthrax",
]


async def seed_keywords(terms: list[str]) -> None:
    added, skipped = [], []
    async with AsyncSessionLocal() as session:
        repo = KeywordRepository(session)
        for term in terms:
            term = term.strip()
            if not term:
                continue
            if await repo.get_by_term(term):
                skipped.append(term)
                continue
            session.add(Keyword(term=term, is_active=True))
            added.append(term)
        await session.commit()

    print(f"Added {len(added)} keyword(s): {added}")
    if skipped:
        print(f"Skipped {len(skipped)} existing: {skipped}")


def main() -> None:
    terms = sys.argv[1:] or DEFAULT_KEYWORDS
    asyncio.run(seed_keywords(terms))


if __name__ == "__main__":
    main()
