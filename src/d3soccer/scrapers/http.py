"""
One HTTP client for every scraper. Many athletics sites (and their CDNs) turn
away requests that identify as a bot, and some also check that the TLS
handshake looks like a real browser's, so requests go out through curl_cffi
impersonating Chrome. Timeouts and 429/5xx responses get retried with backoff;
other errors (403, 404) are raised straight away.

Sites behind AWS WAF's bot control answer even that with a 405 JavaScript
challenge. For those, the page is loaded in headless Chromium, which runs the
challenge; the browser keeps the cookie it earns, so later pages on the same
site load directly. The Refresh data workflow installs Chromium for this.
"""

from __future__ import annotations

import atexit
import time
from dataclasses import dataclass

from curl_cffi import requests as cffi_requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

__all__ = ["HTTPError", "RequestException", "get"]

# Status codes that mean "prove you're a browser" rather than a real error.
CHALLENGE_STATUSES = {202, 405}

TIMEOUT = 30
ATTEMPTS = 3
HEADERS = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

_session = cffi_requests.Session(impersonate="chrome")


def get(url: str, *, headers: dict | None = None, timeout: float = TIMEOUT):
    """GET `url` like Chrome would; raises HTTPError for a non-2xx final response."""
    for attempt in range(1, ATTEMPTS + 1):
        try:
            resp = _session.get(url, headers={**HEADERS, **(headers or {})}, timeout=timeout)
            if resp.status_code in CHALLENGE_STATUSES:
                return _browser_get(url)
            if resp.status_code != 429 and resp.status_code < 500:
                resp.raise_for_status()
                return resp
            if attempt == ATTEMPTS:
                resp.raise_for_status()
        except HTTPError:
            raise
        except RequestException:
            if attempt == ATTEMPTS:
                raise
        time.sleep(2**attempt)
    raise AssertionError("unreachable")


@dataclass
class BrowserResponse:
    url: str
    text: str
    status_code: int = 200


_browser = None


def _browser_get(url: str) -> BrowserResponse:
    """Load `url` in a shared headless Chromium and return the page once it settles."""
    global _browser
    if _browser is None:
        from playwright.sync_api import sync_playwright

        pw = sync_playwright().start()
        launched = pw.chromium.launch()
        _browser = launched.new_context(locale="en-US")

        def close():
            launched.close()
            pw.stop()

        atexit.register(close)

    page = _browser.new_page()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=TIMEOUT * 1000)
        try:
            # The challenge script reloads the page when it passes.
            page.wait_for_load_state("networkidle", timeout=TIMEOUT * 1000)
        except Exception:
            pass
        return BrowserResponse(url=page.url, text=page.content())
    finally:
        page.close()
