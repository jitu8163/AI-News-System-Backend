from __future__ import annotations

import asyncio
import json
import re
import urllib.parse

import httpx
import trafilatura

from app.utils.logging import get_logger

logger = get_logger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

# Google News RSS article links look like
# https://news.google.com/rss/articles/CBMi...  — the id encodes the real URL.
_GN_ARTICLE_RE = re.compile(r"news\.google\.com/rss/articles/([^?/]+)")
_GN_SIG_RE = re.compile(r'data-n-a-sg="([^"]+)"')
_GN_TS_RE = re.compile(r'data-n-a-ts="([^"]+)"')


async def _decode_google_news_url(client: httpx.AsyncClient, url: str) -> str | None:
    """Decode a Google News RSS article URL to the real publisher URL.

    Modern Google News links are NOT plain HTTP redirects; the link embeds an
    encoded article id that must be exchanged for the real URL via Google's
    internal ``batchexecute`` endpoint (fetch the article page for a signature +
    timestamp, then POST them back). Returns ``None`` on any failure so callers
    can fall back to standard redirect resolution / the RSS summary.
    """
    match = _GN_ARTICLE_RE.search(url)
    if not match:
        return None
    gn_id = match.group(1)
    try:
        page = await client.get(f"https://news.google.com/rss/articles/{gn_id}")
        sig = _GN_SIG_RE.search(page.text)
        ts = _GN_TS_RE.search(page.text)
        if not (sig and ts):
            return None

        inner = [
            "garturlreq",
            [
                ["X", "X", ["X", "X"], None, None, 1, 1, "US:en", None, 1,
                 None, None, None, None, None, 0, 1],
                "X", "X", 1, [1, 1, 1], 1, 1, None, 0, 0, None, 0,
            ],
            gn_id,
            int(ts.group(1)),
            sig.group(1),
        ]
        req = [[["Fbv4je", json.dumps(inner), None, "generic"]]]
        payload = "f.req=" + urllib.parse.quote(json.dumps(req))

        resp = await client.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            content=payload,
            headers={"content-type": "application/x-www-form-urlencoded;charset=UTF-8"},
        )
        # Response is chunked text; the JSON payload is the second block.
        parts = resp.text.split("\n\n")
        body = parts[1] if len(parts) > 1 else resp.text
        data = json.loads(body)
        decoded = json.loads(data[0][2])[1]
        if isinstance(decoded, str) and decoded.startswith("http"):
            logger.debug("gn_decoded", final=decoded[:80])
            return decoded
    except Exception as exc:  # noqa: BLE001 — decoding is best-effort
        logger.debug("gn_decode_failed", error=str(exc))
    return None


async def _resolve_url(url: str) -> str:
    """Resolve a feed URL to the real publisher URL.

    Google News links are decoded via ``batchexecute``; everything else (and any
    decode failure) falls back to following standard HTTP redirects.
    """
    async with httpx.AsyncClient(
        follow_redirects=True,
        timeout=20,
        headers=_HEADERS,
    ) as client:
        if "news.google.com" in url:
            decoded = await _decode_google_news_url(client, url)
            if decoded:
                return decoded
        try:
            r = await client.head(url)
            final = str(r.url)
            if final != url:
                logger.debug("redirect_resolved", original=url[:60], final=final[:60])
            return final
        except Exception:
            return url


def _trafilatura_extract(url: str) -> str | None:
    downloaded = trafilatura.fetch_url(
        url,
        config=trafilatura.settings.use_config(),
    )
    if not downloaded:
        return None
    return trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=False,
        no_fallback=False,
    )


def _newspaper_extract(url: str) -> str | None:
    try:
        from newspaper import Article
        article = Article(url, headers=_HEADERS)
        article.download()
        article.parse()
        return article.text or None
    except Exception as exc:
        logger.debug("newspaper_failed", url=url[:60], error=str(exc))
        return None


async def extract_content(url: str) -> str | None:
    # Resolve Google News (and other) redirects to the real article before extraction
    real_url = await _resolve_url(url)

    loop = asyncio.get_event_loop()

    content = await loop.run_in_executor(None, _trafilatura_extract, real_url)
    if content and len(content.strip()) > 100:
        return content.strip()

    logger.debug("trafilatura_fallback", url=real_url[:60])
    content = await loop.run_in_executor(None, _newspaper_extract, real_url)
    if content and len(content.strip()) > 100:
        return content.strip()

    logger.warning("extraction_failed", url=real_url[:60])
    return None
