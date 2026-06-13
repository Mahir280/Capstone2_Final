"""Rate-limited, cached fetching for Google Patents pages."""

from __future__ import annotations

import hashlib
import json
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import httpx

GOOGLE_PATENTS_HOST = "patents.google.com"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
BLOCK_PAGE_MARKERS = (
    "your computer or network may be sending automated queries",
    "to protect our users, we can't process your request right now",
)
PUBLICATION_NUMBER_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]+$")


class PatentPageFetchError(RuntimeError):
    """Raised when a patent page cannot be fetched after bounded retries."""


@dataclass(frozen=True)
class CachedPatentPage:
    """A fetched page and the local file that stores it."""

    url: str
    content: str
    cache_path: Path
    from_cache: bool


class PatentPageFetcher:
    """Fetch Google Patents pages with pacing, backoff, and a disk cache."""

    def __init__(
        self,
        cache_dir: str | Path = "data/cache/google_patents",
        *,
        min_delay_seconds: float = 12.0,
        jitter_seconds: float = 3.0,
        max_retries: int = 5,
        backoff_base_seconds: float = 30.0,
        backoff_cap_seconds: float = 120.0,
        timeout_seconds: float = 30.0,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
        monotonic: Callable[[], float] = time.monotonic,
        random_uniform: Callable[[float, float], float] = random.uniform,
    ) -> None:
        if min_delay_seconds < 0 or jitter_seconds < 0:
            raise ValueError("Request delays must be non-negative")
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")

        self.cache_dir = Path(cache_dir)
        self.min_delay_seconds = min_delay_seconds
        self.jitter_seconds = jitter_seconds
        self.max_retries = max_retries
        self.backoff_base_seconds = backoff_base_seconds
        self.backoff_cap_seconds = backoff_cap_seconds
        self._sleep = sleep
        self._monotonic = monotonic
        self._random_uniform = random_uniform
        self._last_request_started: float | None = None
        self._owns_client = client is None
        self._client = client or httpx.Client(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "fiber-wearable-patent-mapping/1.0 "
                    "(research corpus; low-frequency requests)"
                )
            },
        )

    def __enter__(self) -> PatentPageFetcher:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def fetch(
        self, publication_or_url: str, *, refresh: bool = False
    ) -> CachedPatentPage:
        """Return a cached page, fetching it only when necessary."""
        url = self.normalize_url(publication_or_url)
        cache_path = self.cache_path_for(url)
        if cache_path.exists() and not refresh:
            return CachedPatentPage(
                url=url,
                content=cache_path.read_text(encoding="utf-8"),
                cache_path=cache_path,
                from_cache=True,
            )

        response = self._request_with_backoff(url)
        self._write_cache(cache_path, response.text)
        self._write_metadata(cache_path, url, response)
        return CachedPatentPage(
            url=url,
            content=response.text,
            cache_path=cache_path,
            from_cache=False,
        )

    def cache_path_for(self, publication_or_url: str) -> Path:
        url = self.normalize_url(publication_or_url)
        path_parts = [part for part in urlsplit(url).path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "patent":
            stem = re.sub(r"[^A-Za-z0-9._-]", "_", path_parts[1])
        else:
            stem = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20]
        return self.cache_dir / f"{stem}.html"

    @staticmethod
    def normalize_url(publication_or_url: str) -> str:
        value = publication_or_url.strip()
        if PUBLICATION_NUMBER_PATTERN.fullmatch(value.upper()):
            return f"https://{GOOGLE_PATENTS_HOST}/patent/{value.upper()}/en"

        parts = urlsplit(value)
        if parts.scheme != "https" or parts.hostname != GOOGLE_PATENTS_HOST:
            raise ValueError("Only HTTPS Google Patents URLs are supported")
        path_parts = [part for part in parts.path.split("/") if part]
        if len(path_parts) >= 2 and path_parts[0] == "patent":
            publication_number = path_parts[1].upper()
            if not PUBLICATION_NUMBER_PATTERN.fullmatch(publication_number):
                raise ValueError("Invalid Google Patents publication number")
            normalized_path = f"/patent/{publication_number}/en"
        else:
            normalized_path = parts.path.rstrip("/") or "/"
        return urlunsplit(
            ("https", GOOGLE_PATENTS_HOST, normalized_path, parts.query, "")
        )

    def _request_with_backoff(self, url: str) -> httpx.Response:
        last_reason = "unknown error"
        for attempt in range(self.max_retries + 1):
            self._wait_for_request_slot()
            try:
                response = self._client.get(url)
            except httpx.RequestError as exc:
                last_reason = str(exc)
                if attempt == self.max_retries:
                    break
                self._sleep(self._backoff_seconds(attempt, None))
                continue

            blocked = self._is_block_page(response.text)
            if response.status_code not in RETRYABLE_STATUS_CODES and not blocked:
                try:
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    raise PatentPageFetchError(
                        f"Google Patents returned HTTP {response.status_code} for {url}"
                    ) from exc
                return response

            last_reason = (
                "Google automated-query block page"
                if blocked
                else f"HTTP {response.status_code}"
            )
            if attempt == self.max_retries:
                break
            retry_after = self._retry_after_seconds(response)
            self._sleep(self._backoff_seconds(attempt, retry_after))

        raise PatentPageFetchError(
            f"Unable to fetch {url} after {self.max_retries + 1} attempts: "
            f"{last_reason}"
        )

    def _wait_for_request_slot(self) -> None:
        now = self._monotonic()
        if self._last_request_started is not None:
            target_delay = self.min_delay_seconds + self._random_uniform(
                0.0, self.jitter_seconds
            )
            remaining = target_delay - (now - self._last_request_started)
            if remaining > 0:
                self._sleep(remaining)
        self._last_request_started = self._monotonic()

    def _backoff_seconds(
        self, attempt: int, retry_after_seconds: float | None
    ) -> float:
        if retry_after_seconds is not None:
            return min(retry_after_seconds, self.backoff_cap_seconds)
        exponential = self.backoff_base_seconds * (2**attempt)
        jitter = self._random_uniform(0.0, self.jitter_seconds)
        return min(exponential + jitter, self.backoff_cap_seconds)

    @staticmethod
    def _is_block_page(content: str) -> bool:
        lowered = content.lower()
        return any(marker in lowered for marker in BLOCK_PAGE_MARKERS)

    @staticmethod
    def _retry_after_seconds(response: httpx.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(value)
            except (TypeError, ValueError):
                return None
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=UTC)
            return max(0.0, (retry_at - datetime.now(UTC)).total_seconds())

    def _write_cache(self, cache_path: Path, content: str) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = cache_path.with_suffix(".html.tmp")
        temporary_path.write_text(content, encoding="utf-8")
        temporary_path.replace(cache_path)

    @staticmethod
    def _write_metadata(cache_path: Path, url: str, response: httpx.Response) -> None:
        metadata_path = cache_path.with_suffix(".json")
        metadata = {
            "url": url,
            "fetched_at": datetime.now(UTC).isoformat(),
            "status_code": response.status_code,
        }
        temporary_path = metadata_path.with_suffix(".json.tmp")
        temporary_path.write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(metadata_path)
