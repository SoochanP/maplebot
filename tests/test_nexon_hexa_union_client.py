from __future__ import annotations

import asyncio
import copy
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from app.clients.nexon_maple import NexonMapleClient, NexonMapleClientConfig
from app.core.exceptions import EmptyHexaError, EmptyUnionError
from app.core.http_client import HttpClientManager, HttpClientSettings


FIXTURES_DIR = Path(__file__).parent / "fixtures"
_KST = timezone(timedelta(hours=9))


def load_json_fixture(name: str) -> object:
    return json.loads((FIXTURES_DIR / name).read_text(encoding="utf-8-sig"))


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


def test_fetch_hexa_overview_parses_verified_live_shape_fixture() -> None:
    hexa_payload = load_json_fixture("nexon_hexa.json")
    hexa_stat_payload = load_json_fixture("nexon_hexa_stat.json")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix":
            return httpx.Response(200, json=hexa_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix-stat":
            return httpx.Response(200, json=hexa_stat_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_hexa_overview("창킬"))

    assert [core.core_type for core in overview.cores] == ["스킬 코어", "마스터리 코어", "강화 코어", "공용 코어"]
    assert overview.cores[1].linked_skills == ["다크 임페일 VI", "다크 신서시스 VI"]
    assert overview.cores[3].linked_skills == ["솔 야누스", "솔 야누스 : 새벽", "솔 야누스 : 황혼"]
    assert [stat_set.label for stat_set in overview.stat_sets] == ["HEXA 스탯 I", "HEXA 스탯 II", "HEXA 스탯 III"]
    assert overview.stat_sets[2].cores[0].main_stat_name == "크리티컬 데미지 증가"


def test_fetch_hexa_overview_raises_empty_when_core_and_stat_lists_are_empty() -> None:
    hexa_payload = {"date": None, "character_hexa_core_equipment": []}
    hexa_stat_payload = {
        "date": None,
        "character_class": "다크나이트",
        "character_hexa_stat_core": [],
        "character_hexa_stat_core_2": [],
        "character_hexa_stat_core_3": [],
        "preset_hexa_stat_core": [],
        "preset_hexa_stat_core_2": [],
        "preset_hexa_stat_core_3": [],
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix":
            return httpx.Response(200, json=hexa_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix-stat":
            return httpx.Response(200, json=hexa_stat_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyHexaError, match="HEXA 정보가 없습니다."):
        run_client_call(client_manager, client.fetch_hexa_overview("창킬"))


def test_fetch_hexa_overview_allows_nullable_optional_fields() -> None:
    hexa_payload = copy.deepcopy(load_json_fixture("nexon_hexa.json"))
    hexa_stat_payload = copy.deepcopy(load_json_fixture("nexon_hexa_stat.json"))
    hexa_payload["character_hexa_core_equipment"][0]["hexa_core_type"] = None
    hexa_payload["character_hexa_core_equipment"][0]["linked_skill"] = []
    hexa_stat_payload["character_hexa_stat_core"][0]["sub_stat_name_2"] = None
    hexa_stat_payload["character_hexa_stat_core"][0]["sub_stat_level_2"] = None

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix":
            return httpx.Response(200, json=hexa_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/character/hexamatrix-stat":
            return httpx.Response(200, json=hexa_stat_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_hexa_overview("창킬"))

    assert overview.cores[0].core_type is None
    assert overview.cores[0].linked_skills == []
    assert overview.stat_sets[0].cores[0].sub_stat_name_2 is None
    assert overview.stat_sets[0].cores[0].sub_stat_level_2 is None


def test_fetch_union_overview_parses_verified_live_shape_fixture() -> None:
    union_payload = load_json_fixture("nexon_union.json")
    artifact_payload = load_json_fixture("nexon_union_artifact.json")
    champion_payload = load_json_fixture("nexon_union_champion.json")

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(200, json=union_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-artifact":
            return httpx.Response(200, json=artifact_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-champion":
            return httpx.Response(200, json=champion_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_union_overview("창킬"))

    assert overview.union_level == 9867
    assert overview.union_grade == "그랜드 마스터 유니온 4"
    assert [effect.name for effect in overview.artifact_effects] == [
        "올스탯 150 증가",
        "공격력 30, 마력 30 증가",
        "데미지 15.00% 증가",
        "보스 몬스터 공격 시 데미지 15.00% 증가",
    ]
    assert [champion.grade for champion in overview.champions] == ["SSS", "SS", "SS", "C"]
    assert overview.champion_badge_totals[0] == "올스탯 80, 최대 HP/MP 4000 증가"


def test_fetch_union_overview_handles_missing_artifact_data_and_empty_champions() -> None:
    union_payload = load_json_fixture("nexon_union.json")
    champion_payload = {"date": None, "union_champion": [], "champion_badge_total_info": []}

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(200, json=union_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-artifact":
            return httpx.Response(400, json={"error": {"name": "missing", "message": "missing"}}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-champion":
            return httpx.Response(200, json=champion_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_union_overview("창킬"))

    assert overview.union_level == 9867
    assert overview.union_artifact_remain_ap is None
    assert overview.artifact_effects == []
    assert overview.champions == []
    assert overview.champion_badge_totals == []


def test_fetch_union_overview_allows_nullable_optional_fields() -> None:
    union_payload = copy.deepcopy(load_json_fixture("nexon_union.json"))
    artifact_payload = copy.deepcopy(load_json_fixture("nexon_union_artifact.json"))
    champion_payload = copy.deepcopy(load_json_fixture("nexon_union_champion.json"))
    union_payload["union_grade"] = None
    union_payload["union_artifact_level"] = None
    artifact_payload["union_artifact_effect"][0]["level"] = None
    champion_payload["union_champion"][0]["champion_grade"] = None
    champion_payload["union_champion"][0]["champion_class"] = None

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(200, json=union_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-artifact":
            return httpx.Response(200, json=artifact_payload, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union-champion":
            return httpx.Response(200, json=champion_payload, headers={"content-type": "application/json"})
        raise AssertionError(f"Unexpected path: {request.url.path}")

    client_manager, client = build_client(httpx.MockTransport(handler))

    overview = run_client_call(client_manager, client.fetch_union_overview("창킬"))

    assert overview.union_grade is None
    assert overview.union_artifact_level is None
    assert overview.artifact_effects[0].level is None
    assert overview.champions[0].grade is None
    assert overview.champions[0].class_name is None


def test_fetch_union_overview_raises_empty_when_union_summary_is_missing() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/maplestory/v1/id":
            return httpx.Response(200, json={"ocid": "ocid-123"}, headers={"content-type": "application/json"})
        if request.url.path == "/maplestory/v1/user/union":
            return httpx.Response(400, json={"error": {"name": "missing", "message": "missing"}}, headers={"content-type": "application/json"})
        return httpx.Response(200, json={"date": None}, headers={"content-type": "application/json"})

    client_manager, client = build_client(httpx.MockTransport(handler))

    with pytest.raises(EmptyUnionError, match="유니온 정보가 없습니다."):
        run_client_call(client_manager, client.fetch_union_overview("창킬"))
