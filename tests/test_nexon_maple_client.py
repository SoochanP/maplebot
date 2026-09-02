from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from app.clients.nexon_maple import NexonMapleClient, NexonMapleClientConfig
from app.core.exceptions import (
    CharacterNotFoundError,
    ConfigurationError,
    EmptyHexaError,
    EmptyHistoryError,
    EmptyNoticeError,
    EmptyUnionError,
    ExternalSiteUnavailableError,
    RankingUnavailableError,
)
from app.core.http_client import HttpClientManager, HttpClientSettings


_KST = timezone(timedelta(hours=9))


def build_client(
    handler: httpx.MockTransport | httpx.AsyncBaseTransport,
    *,
    api_key: str | None = "test-key",
    now: datetime | None = None,
    config: NexonMapleClientConfig | None = None,
) -> tuple[HttpClientManager, NexonMapleClient]:
    client_manager = HttpClientManager(
        settings=HttpClientSettings(),
        transport=handler,
    )
    client = NexonMapleClient(
        http_client_manager=client_manager,
        api_key=api_key,
        config=config,
        now_provider=(None if now is None else lambda: now),
    )
    return client_manager, client


def run_client_call(client_manager: HttpClientManager, coroutine):
    async def run():
        await client_manager.start()
        try:
            return await coroutine
        finally:
            await client_manager.close()

    return asyncio.run(run())


def test_resolve_ocid_sends_api_key_header() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/maplestory/v1/id"
        assert request.headers["x-nxopen-api-key"] == "test-key"
        assert request.url.params["character_name"] == "창킬"
        return httpx.Response(
            200,
            json={"ocid": "ocid-123"},
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    ocid = run_client_call(client_manager, client.resolve_ocid("창킬"))

    assert ocid == "ocid-123"


def test_resolve_ocid_raises_character_not_found_on_bad_request() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error": {"name": "OPENAPI00007", "message": "not found"}},
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(CharacterNotFoundError, match="캐릭터를 찾을 수 없습니다."):
        run_client_call(client_manager, client.resolve_ocid("없는이름"))


def test_resolve_ocid_raises_configuration_error_when_api_key_missing() -> None:
    client_manager, client = build_client(
        httpx.MockTransport(lambda request: httpx.Response(200, json={"ocid": "unused"})),
        api_key=None,
    )

    with pytest.raises(ConfigurationError, match="NEXON API 키 설정이 필요합니다."):
        run_client_call(client_manager, client.resolve_ocid("창킬"))


def test_resolve_ocid_raises_configuration_error_for_invalid_api_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={"error": {"name": "OPENAPI00001", "message": "forbidden"}},
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(ConfigurationError, match="현재 NEXON API 설정이 올바르지 않습니다."):
        run_client_call(client_manager, client.resolve_ocid("창킬"))


def test_resolve_ocid_maps_provider_timeout() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(ExternalSiteUnavailableError, match="현재 조회 사이트에 접속할 수 없습니다."):
        run_client_call(client_manager, client.resolve_ocid("창킬"))


def test_fetch_latest_notices_maps_provider_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            503,
            text="unavailable",
            headers={"content-type": "text/plain"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(ExternalSiteUnavailableError, match="현재 조회 사이트에 접속할 수 없습니다."):
        run_client_call(client_manager, client.fetch_latest_notices())


def test_fetch_hexa_overview_maps_core_and_stat_data() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix":
            return httpx.Response(
                200,
                json={
                    "date": "2026-09-02T00:00+09:00",
                    "character_hexa_core_equipment": [
                        {
                            "hexa_core_name": "마스터리 코어",
                            "hexa_core_level": 30,
                            "hexa_core_type": "스킬",
                            "linked_skill": [{"hexa_skill_id": "80002616"}],
                        }
                    ],
                },
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/maplestory/v1/character/hexamatrix-stat":
            return httpx.Response(
                200,
                json={
                    "date": "2026-09-02T00:00+09:00",
                    "character_class": "나이트로드",
                    "character_hexa_stat_core": [
                        {
                            "slot_id": "1",
                            "main_stat_name": "크리티컬 데미지",
                            "sub_stat_name_1": "보스 몬스터 데미지",
                            "sub_stat_name_2": "방어율 무시",
                            "main_stat_level": 10,
                            "sub_stat_level_1": 5,
                            "sub_stat_level_2": 5,
                            "stat_grade": 1,
                        }
                    ],
                    "character_hexa_stat_core_2": [],
                    "character_hexa_stat_core_3": [],
                },
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_hexa_overview("창킬"))

    assert overview.character_name == "창킬"
    assert len(overview.cores) == 1
    assert overview.cores[0].name == "마스터리 코어"
    assert overview.cores[0].linked_skills == ["80002616"]
    assert len(overview.stat_sets) == 1
    assert overview.stat_sets[0].label == "HEXA 스탯 I"
    assert overview.stat_sets[0].cores[0].main_stat_name == "크리티컬 데미지"


def test_fetch_hexa_overview_raises_empty_hexa_when_all_data_missing() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        return httpx.Response(
            400,
            json={"error": {"name": "OPENAPI00004", "message": "missing"}},
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyHexaError, match="HEXA 정보가 없습니다."):
        run_client_call(client_manager, client.fetch_hexa_overview("창킬"))


def test_fetch_union_overview_maps_union_summary() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(
                200,
                json={
                    "date": "2026-09-02T00:00+09:00",
                    "union_level": 9500,
                    "union_grade": "그랜드 마스터 유니온",
                    "union_artifact_level": 60,
                    "union_artifact_exp": 1200,
                    "union_artifact_point": 85,
                },
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/maplestory/v1/user/union-artifact":
            return httpx.Response(
                200,
                json={
                    "date": "2026-09-02T00:00+09:00",
                    "union_artifact_effect": [
                        {"name": "크리티컬 데미지", "level": 5},
                        {"name": "보스 몬스터 데미지", "level": 5},
                    ],
                    "union_artifact_remain_ap": 3,
                },
                headers={"content-type": "application/json"},
            )
        if request.url.path == "/maplestory/v1/user/union-champion":
            return httpx.Response(
                200,
                json={
                    "date": "2026-09-02T00:00+09:00",
                    "union_champion": [
                        {
                            "champion_name": "부캐1",
                            "champion_grade": "S",
                            "champion_class": "나이트로드",
                            "champion_badge_info": [{"stat": "보스 몬스터 데미지 +1%"}],
                        }
                    ],
                    "champion_badge_total_info": [{"stat": "크리티컬 데미지 +2%"}],
                },
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_union_overview("창킬"))

    assert overview.character_name == "창킬"
    assert overview.union_level == 9500
    assert overview.union_grade == "그랜드 마스터 유니온"
    assert overview.union_artifact_remain_ap == 3
    assert [effect.name for effect in overview.artifact_effects] == ["크리티컬 데미지", "보스 몬스터 데미지"]
    assert [champion.name for champion in overview.champions] == ["부캐1"]
    assert overview.champion_badge_totals == ["크리티컬 데미지 +2%"]


def test_fetch_union_overview_raises_empty_union_when_main_payload_missing() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(400, json={"error": {"name": "missing", "message": "missing"}}, headers={"content-type": "application/json"})
        return httpx.Response(200, json={"date": "2026-09-02T00:00+09:00"}, headers={"content-type": "application/json"})

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyUnionError, match="유니온 정보가 없습니다."):
        run_client_call(client_manager, client.fetch_union_overview("창킬"))


def test_fetch_overall_ranking_falls_back_to_previous_day() -> None:
    requested_dates: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/ranking/overall":
            requested_dates.append(request.url.params["date"])
            if request.url.params["date"] == "2026-09-02":
                return httpx.Response(400, json={"error": {"name": "not-ready", "message": "not ready"}}, headers={"content-type": "application/json"})
            return httpx.Response(
                200,
                json={
                    "ranking": [
                        {
                            "date": "2026-09-01",
                            "ranking": 12345,
                            "character_name": "창킬",
                            "world_name": "스카니아",
                            "class_name": "나이트로드",
                            "sub_class_name": "나이트로드",
                            "character_level": 290,
                        }
                    ]
                },
                headers={"content-type": "application/json"},
            )
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(
        httpx.MockTransport(handler),
        now=datetime(2026, 9, 2, 8, 0, tzinfo=_KST),
    )

    ranking = run_client_call(client_manager, client.fetch_overall_ranking("창킬"))

    assert requested_dates == ["2026-09-02", "2026-09-01"]
    assert ranking.ranking == 12345
    assert ranking.ranking_date.isoformat() == "2026-09-01"
    assert ranking.world_name == "스카니아"


def test_fetch_overall_ranking_raises_unavailable_when_no_recent_rank_exists() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        return httpx.Response(400, json={"error": {"name": "not-ready", "message": "not ready"}}, headers={"content-type": "application/json"})

    client_manager, client = build_client(
        httpx.MockTransport(handler),
        now=datetime(2026, 9, 2, 8, 0, tzinfo=_KST),
    )

    with pytest.raises(RankingUnavailableError, match="현재 랭킹 정보를 확인할 수 없습니다."):
        run_client_call(client_manager, client.fetch_overall_ranking("창킬"))


def test_fetch_latest_notices_sorts_and_limits_latest_five() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/maplestory/v1/notice"
        return httpx.Response(
            200,
            json={
                "notice": [
                    {"title": "3", "url": "https://example.com/3", "date": "2026-09-01T12:00+09:00"},
                    {"title": "6", "url": "https://example.com/6", "date": "2026-09-02T15:00+09:00"},
                    {"title": "2", "url": "https://example.com/2", "date": "2026-08-31T12:00+09:00"},
                    {"title": "5", "url": "https://example.com/5", "date": "2026-09-02T10:00+09:00"},
                    {"title": "1", "url": "https://example.com/1", "date": "2026-08-30T12:00+09:00"},
                    {"title": "4", "url": "https://example.com/4", "date": "2026-09-01T18:00+09:00"},
                ]
            },
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(httpx.MockTransport(handler))

    feed = run_client_call(client_manager, client.fetch_latest_notices())

    assert [item.title for item in feed.items] == ["6", "5", "4", "3", "2"]


def test_fetch_latest_notices_raises_empty_notice_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"notice": []}, headers={"content-type": "application/json"})

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyNoticeError, match="공지 정보가 없습니다."):
        run_client_call(client_manager, client.fetch_latest_notices())


def test_fetch_experience_history_collects_valid_daily_snapshots_in_chronological_order() -> None:
    requested_dates: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path != "/maplestory/v1/character/basic":
            raise AssertionError(f"Unexpected path: {request.url.path}")

        requested_date = request.url.params["date"]
        requested_dates.append(requested_date)
        if requested_date in {"2026-09-01", "2026-08-29"}:
            return httpx.Response(400, json={"error": {"name": "missing", "message": "missing"}}, headers={"content-type": "application/json"})
        if requested_date == "2026-08-30":
            await asyncio.sleep(0.01)
        if requested_date == "2026-08-31":
            await asyncio.sleep(0.02)

        level = 290 if requested_date != "2026-08-28" else 289
        experience = {
            "2026-09-02": 3400,
            "2026-08-31": 3100,
            "2026-08-30": 2800,
            "2026-08-28": 9800,
            "2026-08-27": 9500,
            "2026-08-26": 9200,
            "2026-08-25": 8900,
            "2026-08-24": 8600,
        }[requested_date]
        percent = {
            "2026-09-02": "34.129",
            "2026-08-31": "31.442",
            "2026-08-30": "27.155",
            "2026-08-28": "98.500",
            "2026-08-27": "95.000",
            "2026-08-26": "92.000",
            "2026-08-25": "89.000",
            "2026-08-24": "86.000",
        }[requested_date]
        return httpx.Response(
            200,
            json={
                "date": f"{requested_date}T00:00+09:00",
                "character_name": "창킬",
                "character_level": level,
                "character_exp": experience,
                "character_exp_rate": percent,
            },
            headers={"content-type": "application/json"},
        )

    client_manager, client = build_client(
        httpx.MockTransport(handler),
        now=datetime(2026, 9, 2, 12, 0, tzinfo=_KST),
    )

    history = run_client_call(client_manager, client.fetch_experience_history("창킬"))

    assert requested_dates == [
        "2026-09-02",
        "2026-09-01",
        "2026-08-31",
        "2026-08-30",
        "2026-08-29",
        "2026-08-28",
        "2026-08-27",
        "2026-08-26",
        "2026-08-25",
        "2026-08-24",
    ]
    assert [entry.date.isoformat() for entry in history.entries] == [
        "2026-08-24",
        "2026-08-25",
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
        "2026-08-30",
        "2026-08-31",
        "2026-09-02",
    ]
    assert history.entries[-1].experience == 3400


def test_fetch_experience_history_raises_empty_history_when_no_snapshots_exist() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        return httpx.Response(400, json={"error": {"name": "missing", "message": "missing"}}, headers={"content-type": "application/json"})

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyHistoryError, match="경험치 히스토리가 없습니다."):
        run_client_call(client_manager, client.fetch_experience_history("창킬"))




