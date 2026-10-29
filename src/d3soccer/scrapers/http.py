"""
One HTTP client for every scraper. Many athletics sites (and their CDNs) turn
away requests that identify as a bot, and some also check that the TLS
handshake looks like a real browser's, so requests go out through curl_cffi
impersonating Chrome. Timeouts and 429/5xx responses get retried with backoff;
other errors (403, 404) are raised straight away.
"""

from __future__ import annotations

import time

from curl_cffi import requests as cffi_requests
from curl_cffi.requests.exceptions import HTTPError, RequestException

__all__ = ["HTTPError", "RequestException", "get", "get_raw"]

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


def get_raw(url: str, *, timeout: float = TIMEOUT):
    """One Chrome-like GET with no retries or status check (for the probe)."""
    return _session.get(url, headers=HEADERS, timeout=timeout)
