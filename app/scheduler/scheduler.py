from __future__ import annotations

from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.ai.processor import process_article
from app.collectors.extractor import extract_content
from app.collectors.news_collector import fetch_for_keyword
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.article import Article, ArticleKeyword
from app.repositories.article_repository import ArticleRepository
from app.repositories.keyword_repository import KeywordRepository
from app.services.settings_store import get_monitored_countries
from app.utils.logging import get_logger

logger = get_logger(__name__)

_scheduler = AsyncIOScheduler()


# UTC recency window for India-wide news collection. Articles are considered
# recent relative to UTC, since the platform tracks many Indian states.
_UTC = timezone.utc

# How many UTC calendar days back count as "recent". 1 == today only,
# 2 == today + yesterday, etc.
RECENT_DAYS = 2


def _published_recently(raw) -> bool:
    """True if the article was published within the last ``RECENT_DAYS`` UTC days.

    Articles without a publish date can't be confirmed as recent, so they're
    excluded (we only want fresh news).
    """
    pub = raw.published_date
    if pub is None:
        return False
    if pub.tzinfo is None:  # treat naive feed dates as UTC
        pub = pub.replace(tzinfo=timezone.utc)
    earliest = datetime.now(_UTC).date() - timedelta(days=RECENT_DAYS - 1)
    return pub.astimezone(_UTC).date() >= earliest


async def collect_and_process() -> None:
    logger.info("news_job_start")
    async with AsyncSessionLocal() as session:
        kw_repo = KeywordRepository(session)
        keywords = await kw_repo.list_active()

        if not keywords:
            logger.info("news_job_no_keywords")
            return

        regions = await get_monitored_countries(session)
    logger.info("news_job_regions", regions=regions)
    for kw in keywords:
        raw_articles = await fetch_for_keyword(kw.id, kw.term, regions)

        # Keep only recent (UTC) articles. Already-saved ones are skipped cheaply
        # inside _save_article (hash check before extraction), so each cycle only
        # does the heavy extraction work for genuinely new articles. No per-cycle
        # cap: process every new recent article.
        recent = [r for r in raw_articles if _published_recently(r)]
        saved = 0
        for raw in recent:
            if await _save_article(raw, keyword_hint=kw.term):
                saved += 1
        logger.info(
            "keyword_done",
            keyword=kw.term,
            new_articles=saved,
            recent_candidates=len(recent),
            skipped_not_recent=len(raw_articles) - len(recent),
        )

    logger.info("news_job_done")


async def _save_article(raw, keyword_hint: str | None = None) -> bool:
    """Save and process one article. Returns True if it was new, False if duplicate."""
    async with AsyncSessionLocal() as session:
        art_repo = ArticleRepository(session)

        if await art_repo.get_by_hash(raw.content_hash):
            return False

        article = Article(
            title=raw.title,
            article_url=raw.url,
            source_name=raw.source_name,
            published_date=raw.published_date,
            content_hash=raw.content_hash,
            country=raw.country,
            rss_summary=raw.rss_summary,
        )
        session.add(article)
        await session.flush()
        session.add(ArticleKeyword(article_id=article.id, keyword_id=raw.keyword_id))

        content = await extract_content(raw.url)
        if not content:
            if raw.rss_summary and len(raw.rss_summary) > 30:
                content = raw.rss_summary
                logger.debug("using_rss_summary", url=raw.url[:60])
            else:
                article.extraction_failed = True
                await session.commit()
                return True

        article.content = content

        try:
            ai = await process_article(raw.title, content, keyword_hint=keyword_hint)
            article.disease_name = ai["disease_name"]
            article.disease_category = ai["disease_category"]
            article.human_health_impact = ai["human_health_impact"]
            article.animal_health_impact = ai["animal_health_impact"]
            article.environmental_health_impact = ai["environmental_health_impact"]
            article.symptoms = ai["symptoms"]
            article.death_count = ai["death_count"]
            article.positive_cases = ai["positive_cases"]
            article.suspected_cases = ai["suspected_cases"]
            article.species_affected = ai["species_affected"]
            article.environmental_factors = ai["environmental_factors"]
            article.risk_level = ai["risk_level"]
            article.event_date = ai["event_date"]
            article.ai_summary = ai["ai_summary"]
            # When we collected for a specific state, that state is authoritative
            # (the user asked for that state's news). Only fall back to the
            # AI-detected state for All-India collection (raw.country is None).
            article.country = raw.country or ai.get("country")
            article.ai_processed = True
        except Exception as exc:
            logger.error("ai_failed", url=raw.url, error=str(exc))

        await session.commit()
        logger.info("article_saved", title=raw.title[:80])
        return True


_current_interval_hours: int = settings.NEWS_FETCH_INTERVAL_HOURS

VALID_INTERVALS = [0.25, 0.5, 1, 2, 4, 6, 8, 12]


def get_interval_hours() -> float:
    return _current_interval_hours


def update_interval(hours: float) -> None:
    global _current_interval_hours
    _current_interval_hours = hours
    if _scheduler.running:
        minutes = int(hours * 60)
        _scheduler.reschedule_job(
            "news_collect",
            trigger="interval",
            minutes=minutes,
        )
    logger.info("scheduler_interval_updated", hours=hours)


def start_scheduler() -> None:
    """Start the background news scheduler. Safe to call once on app startup.

    Idempotent (won't double-start) and never raises into the caller, so a
    scheduler problem is logged loudly but can't crash application boot.
    """
    if _scheduler.running:
        logger.info("scheduler_already_running")
        return

    minutes = int(_current_interval_hours * 60)
    try:
        _scheduler.add_job(
            collect_and_process,
            trigger="interval",
            minutes=minutes,
            id="news_collect",
            replace_existing=True,
            # A full sweep (all keywords x all states) can run longer than one
            # interval. coalesce + max_instances=1 collapse any ticks that pile
            # up during a long run into a single next run instead of silently
            # dropping them as misfires; the wide grace window keeps a delayed
            # run alive rather than skipping it.
            coalesce=True,
            max_instances=1,
            misfire_grace_time=3600,
            # Run once immediately on startup so a fresh deploy captures the whole
            # day's articles right away, then repeats every interval.
            next_run_time=datetime.now(_UTC),
        )
        _scheduler.start()
        logger.info(
            "scheduler_started",
            interval_hours=_current_interval_hours,
            running=_scheduler.running,
        )
    except Exception:
        logger.exception("scheduler_start_failed")


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("scheduler_stopped")
