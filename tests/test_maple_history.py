from __future__ import annotations

import asyncio
import json
from pathlib import Path

import httpx
import pytest

from app.core.exceptions import (
    CharacterNotFoundError,
    EmptyHistoryError,
    ExternalSiteUnavailableError,
)
from app.core.http_client import HttpClientManager, HttpClientSettings
from app.crawlers.maple_history import MapleHistoryCrawler, MapleHistoryCrawlerConfig


FIXTURES_DIR = Path(__file__).parent / "fixtures"
CHARACTERS_FIXTURE_PATH = FIXTURES_DIR / "maple_history_get_characters.json"
BASIC_LOGS_FIXTURE_PATH = FIXTURES_DIR / "maple_history_basic_logs.json"


def load_json_fixture(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_crawler(
    transport: httpx.AsyncBaseTransport,
    *,
    config: MapleHistoryCrawlerConfig | None = None,
) -> tuple[HttpClientManager, MapleHistoryCrawler]:
    client_manager = HttpClientManager(
        settings=HttpClientSettings(),
        transport=transport,
    )
    crawler = MapleHistoryCrawler(
        http_client_manager=client_manager,
        config=config or MapleHistoryCrawlerConfig(search_poll_interval_seconds=0),
    )
    return client_manager, crawler


def test_parse_character_search_payload_maps_characters() -> None:
    payload = load_json_fixture(CHARACTERS_FIXTURE_PATH)
    _, crawler = build_crawler(httpx.MockTransport(lambda request: httpx.Response(200, json=[])))

    characters = crawler.parse_character_search_payload(payload)

    assert len(characters) == 1
    assert characters[0].id == "ed6979fb631addf0f5198e7263828f3e"
    assert characters[0].character_name == "창킬"
    assert str(characters[0].character_exp_rate) == "8.369"


def test_parse_basic_log_payload_maps_experience_entries() -> None:
    payload = load_json_fixture(BASIC_LOGS_FIXTURE_PATH)
    _, crawler = build_crawler(httpx.MockTransport(lambda request: httpx.Response(200, json=[])))

    logs = crawler.parse_basic_log_payload(payload)
    history = crawler.parse_experience_history("창킬", logs)

    assert len(history.entries) == 5
    assert history.character_name == "창킬"
    assert history.entries[0].date.isoformat() == "2025-01-08"
    assert history.entries[0].snapshot_at is not None
    assert history.entries[0].snapshot_at.isoformat() == "2025-01-08T00:00:00+09:00"
    assert history.entries[-1].date.isoformat() == "2025-01-12"
    assert str(history.entries[-1].experience_percent) == "41.334"


def test_parse_basic_log_payload_sorts_newest_first_provider_response() -> None:
    payload = list(reversed(load_json_fixture(BASIC_LOGS_FIXTURE_PATH)))
    _, crawler = build_crawler(httpx.MockTransport(lambda request: httpx.Response(200, json=[])))

    logs = crawler.parse_basic_log_payload(payload)

    assert [log.date for log in logs] == sorted(log["date"] for log in payload)
    assert logs[0].character_exp == 46396709843484
    assert logs[-1].character_exp == 60221558626871


def test_parse_basic_log_payload_sorts_unexpected_order_with_duplicate_timestamps() -> None:
    payload = [
        {
            "character_id": "abc",
            "date": 3000,
            "character_name": "창킬",
            "character_level": 290,
            "character_exp": 200,
            "character_exp_rate": "20.000",
        },
        {
            "character_id": "abc",
            "date": 1000,
            "character_name": "창킬",
            "character_level": 289,
            "character_exp": 100,
            "character_exp_rate": "10.000",
        },
        {
            "character_id": "abc",
            "date": 3000,
            "character_name": "창킬",
            "character_level": 290,
            "character_exp": 150,
            "character_exp_rate": "15.000",
        },
    ]
    _, crawler = build_crawler(httpx.MockTransport(lambda request: httpx.Response(200, json=[])))

    logs = crawler.parse_basic_log_payload(payload)

    assert [(log.date, log.character_exp) for log in logs] == [
        (1000, 100),
        (3000, 150),
        (3000, 200),
    ]


def test_fetch_experience_history_success_with_mock_transport() -> None:
    characters_payload = load_json_fixture(CHARACTERS_FIXTURE_PATH)
    logs_payload = load_json_fixture(BASIC_LOGS_FIXTURE_PATH)

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ajax/get-characters":
            assert request.url.params["name"] == "창킬"
            return httpx.Response(
                200,
                json=characters_payload,
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/get-character-logs":
            assert request.url.params["id"] == "ed6979fb631addf0f5198e7263828f3e"
            assert request.url.params["name"] == "basic"
            return httpx.Response(
                200,
                json=logs_payload,
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            history = await crawler.fetch_experience_history("창킬")
        finally:
            await client_manager.close()

        assert history.character_name == "창킬"
        assert [entry.date.isoformat() for entry in history.entries] == [
            "2025-01-08",
            "2025-01-09",
            "2025-01-10",
            "2025-01-11",
            "2025-01-12",
        ]

    asyncio.run(run())


def test_fetch_experience_history_sorts_newest_first_provider_logs() -> None:
    characters_payload = load_json_fixture(CHARACTERS_FIXTURE_PATH)
    logs_payload = list(reversed(load_json_fixture(BASIC_LOGS_FIXTURE_PATH)))

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ajax/get-characters":
            return httpx.Response(
                200,
                json=characters_payload,
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/get-character-logs":
            return httpx.Response(
                200,
                json=logs_payload,
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            history = await crawler.fetch_experience_history("창킬")
        finally:
            await client_manager.close()

        assert [entry.date.isoformat() for entry in history.entries] == [
            "2025-01-08",
            "2025-01-09",
            "2025-01-10",
            "2025-01-11",
            "2025-01-12",
        ]

    asyncio.run(run())


def test_fetch_experience_history_fetches_character_when_lookup_is_empty() -> None:
    characters_payload = load_json_fixture(CHARACTERS_FIXTURE_PATH)
    logs_payload = load_json_fixture(BASIC_LOGS_FIXTURE_PATH)
    search_call_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal search_call_count
        if request.url.path == "/ajax/get-characters":
            search_call_count += 1
            payload = [] if search_call_count == 1 else characters_payload
            return httpx.Response(
                200,
                json=payload,
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/fetch-characters":
            return httpx.Response(
                200,
                json={"code": 103},
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/get-character-logs":
            return httpx.Response(
                200,
                json=logs_payload,
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            history = await crawler.fetch_experience_history("창킬")
        finally:
            await client_manager.close()

        assert history.character_name == "창킬"
        assert search_call_count == 2

    asyncio.run(run())


def test_fetch_experience_history_raises_character_not_found() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ajax/get-characters":
            return httpx.Response(
                200,
                json=[],
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/fetch-characters":
            return httpx.Response(
                200,
                json={"code": 100},
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            with pytest.raises(CharacterNotFoundError, match="캐릭터를 찾을 수 없습니다."):
                await crawler.fetch_experience_history("없는이름")
        finally:
            await client_manager.close()

    asyncio.run(run())


def test_fetch_experience_history_raises_empty_history_error() -> None:
    characters_payload = load_json_fixture(CHARACTERS_FIXTURE_PATH)

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/ajax/get-characters":
            return httpx.Response(
                200,
                json=characters_payload,
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/ajax/get-character-logs":
            return httpx.Response(
                200,
                json=[],
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            with pytest.raises(EmptyHistoryError, match="경험치 히스토리가 없습니다."):
                await crawler.fetch_experience_history("창킬")
        finally:
            await client_manager.close()

    asyncio.run(run())


def test_fetch_experience_history_maps_provider_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            text="<html><body>Service Unavailable</body></html>",
            headers={"content-type": "text/html"},
        )

    client_manager, crawler = build_crawler(httpx.MockTransport(handler))

    async def run() -> None:
        await client_manager.start()
        try:
            with pytest.raises(
                ExternalSiteUnavailableError,
                match="현재 조회 사이트에 접속할 수 없습니다.",
            ):
                await crawler.fetch_experience_history("창킬")
        finally:
            await client_manager.close()

    asyncio.run(run())
