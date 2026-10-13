"""Shared HTTP behavior for scrapers: rate limiting and on-disk caching."""

import hashlib
import time
from pathlib import Path

import httpx

from d3soccer import config


class Scraper:
    """Base class for scrapers. Subclasses implement source-specific parsing."""

    def __init__(
        self,
        cache_dir: Path = config.RAW_DIR,
        delay: float = config.REQUEST_DELAY_SECONDS,
        client: httpx.Client | None = None,
    ) -> None:
        self.cache_dir = cache_dir
        self.delay = delay
        self.client = client or httpx.Client(
            headers={"User-Agent": config.USER_AGENT},
            follow_redirects=True,
            timeout=30,
        )
        self._last_request = 0.0

    def fetch(self, url: str, use_cache: bool = True) -> str:
        """Return the body of `url`, reading from the cache when possible."""
        path = self._cache_path(url)
        if use_cache and path.exists():
            return path.read_text(encoding="utf-8")

        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        response = self.client.get(url)
        self._last_request = time.monotonic()
        response.raise_for_status()

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response.text, encoding="utf-8")
        return response.text

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:16]
        return self.cache_dir / type(self).__name__.lower() / f"{digest}.html"
