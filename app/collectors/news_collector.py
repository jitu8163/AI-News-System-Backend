from __future__ import annotations

import asyncio
import html
import re
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime

import feedparser

from app.collectors.countries import COUNTRIES, WORLDWIDE, edition_params
from app.utils.hashing import compute_content_hash
from app.utils.logging import get_logger

_TAG_RE = re.compile(r"<[^>]+>")

logger = get_logger(__name__)

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={term}&hl={hl}&gl={gl}&ceid={ceid}"


@dataclass
class RawArticle:
    title: str
    url: str
    source_name: str | None
    published_date: datetime | None
    keyword_id: int
    content_hash: str
    rss_summary: str | None = None  # fallback content from RSS feed
    country: str | None = None  # region this article was collected for


def _parse_feed(url: str) -> feedparser.FeedParserDict:
    return feedparser.parse(url)


def _build_feed_url(term: str, region: str | None) -> str:
    hl, gl, ceid = edition_params(region)
    # Scope the query text to the country (except Worldwide, which stays global).
    query = term if (not region or region == WORLDWIDE) else f"{term} {region}"
    return GOOGLE_NEWS_RSS.format(
        term=urllib.parse.quote_plus(query), hl=hl, gl=gl, ceid=ceid
    )


async def _fetch_region(keyword_id: int, term: str, region: str | None) -> list[RawArticle]:
    feed_url = _build_feed_url(term, region)
    loop = asyncio.get_event_loop()
    feed = await loop.run_in_executor(None, _parse_feed, feed_url)

    region_label = None if (not region or region == WORLDWIDE) else region

    articles: list[RawArticle] = []
    for entry in feed.entries:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()
        if not title or not url:
            continue

        source_name: str | None = None
        if hasattr(entry, "source") and isinstance(entry.source, dict):
            source_name = entry.source.get("title")

        pub_date: datetime | None = None
        if entry.get("published"):
            try:
                pub_date = parsedate_to_datetime(entry.published)
            except Exception:
                pass

        # RSS summary is a brief excerpt provided by the publisher — useful
        # as fallback content when full article extraction is blocked.
        raw_summary = entry.get("summary") or ""
        rss_summary = html.unescape(_TAG_RE.sub("", raw_summary)).strip() or None

        articles.append(
            RawArticle(
                title=title,
                url=url,
                source_name=source_name,
                published_date=pub_date,
                keyword_id=keyword_id,
                content_hash=compute_content_hash(title, url),
                rss_summary=rss_summary,
                country=region_label,
            )
        )

    logger.info("rss_fetched", keyword=term, region=region or WORLDWIDE, count=len(articles))
    return articles


async def fetch_for_keyword(
    keyword_id: int, term: str, regions: list[str] | None = None
) -> list[RawArticle]:
    """Fetch articles for a keyword across one or more regions.

    ``regions`` is a list of country names (or ['Worldwide']). Defaults to all
    available countries by default. Duplicate URLs across regions are
    de-duplicated by content hash.
    """
    regions = regions or list(COUNTRIES.keys())

    seen_hashes: set[str] = set()
    articles: list[RawArticle] = []
    for region in regions:
        for raw in await _fetch_region(keyword_id, term, region):
            if raw.content_hash in seen_hashes:
                continue
            seen_hashes.add(raw.content_hash)
            articles.append(raw)

    return articles
