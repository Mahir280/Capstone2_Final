"""Tests for paced and cached Google Patents fetching."""

from __future__ import annotations

import httpx

from src.acquisition.patent_page_fetcher import PatentPageFetcher


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_fetcher_reuses_cached_page_without_network(tmp_path) -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, text="<html>patent</html>", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PatentPageFetcher(
        tmp_path,
        client=client,
        min_delay_seconds=0,
        jitter_seconds=0,
    )

    first = fetcher.fetch("US1234567B2")
    second = fetcher.fetch("https://patents.google.com/patent/us1234567b2/de")

    assert requests == 1
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.content == "<html>patent</html>"


def test_fetcher_spaces_uncached_requests(tmp_path) -> None:
    clock = FakeClock()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html>patent</html>", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PatentPageFetcher(
        tmp_path,
        client=client,
        min_delay_seconds=12,
        jitter_seconds=0,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    fetcher.fetch("US1111111B2")
    fetcher.fetch("US2222222B2")

    assert clock.sleeps == [12.0]


def test_fetcher_honors_retry_after_then_caches_success(tmp_path) -> None:
    clock = FakeClock()
    responses = iter(
        [
            (429, "slow down", {"Retry-After": "45"}),
            (200, "<html>patent</html>", {}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        status, text, headers = next(responses)
        return httpx.Response(status, text=text, headers=headers, request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PatentPageFetcher(
        tmp_path,
        client=client,
        min_delay_seconds=0,
        jitter_seconds=0,
        backoff_base_seconds=30,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    result = fetcher.fetch("US3333333B2")

    assert result.content == "<html>patent</html>"
    assert clock.sleeps == [45.0]


def test_fetcher_retries_google_automated_query_page(tmp_path) -> None:
    clock = FakeClock()
    responses = iter(
        [
            "Your computer or network may be sending automated queries",
            "<html>patent</html>",
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=next(responses), request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PatentPageFetcher(
        tmp_path,
        client=client,
        min_delay_seconds=0,
        jitter_seconds=0,
        backoff_base_seconds=30,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    result = fetcher.fetch("US4444444B2")

    assert result.content == "<html>patent</html>"
    assert clock.sleeps == [30.0]


def test_fetcher_caps_backoff_at_two_minutes(tmp_path) -> None:
    clock = FakeClock()
    responses = iter(
        [
            (429, {"Retry-After": "900"}),
            (200, {}),
        ]
    )

    def handler(request: httpx.Request) -> httpx.Response:
        status, headers = next(responses)
        return httpx.Response(
            status, text="<html>patent</html>", headers=headers, request=request
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    fetcher = PatentPageFetcher(
        tmp_path,
        client=client,
        min_delay_seconds=0,
        jitter_seconds=0,
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )

    fetcher.fetch("US5555555B2")

    assert clock.sleeps == [120.0]
