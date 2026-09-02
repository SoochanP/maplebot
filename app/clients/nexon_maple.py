from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, TypeVar
import asyncio
from collections.abc import Callable, Sequence
from dataclasses import dataclass

import httpx
from pydantic import BaseModel, ValidationError

from app.core.exceptions import (
    CharacterNotFoundError,
    ConfigurationError,
    CrawlerError,
    EmptyHexaError,
    EmptyHistoryError,
    EmptyNoticeError,
    EmptyUnionError,
    ExternalSiteUnavailableError,
    RankingUnavailableError,
)
from app.core.http_client import HttpClientManager
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry
from app.models.hexa import HexaCore, HexaOverview, HexaStatCore, HexaStatSet
from app.models.nexon import (
    NexonCharacterBasicPayload,
    NexonCharacterHexaPayload,
    NexonCharacterHexaStatPayload,
    NexonCharacterIdentifierPayload,
    NexonHexaStatCorePayload,
    NexonNoticePayload,
    NexonOverallRankingPayload,
    NexonUnionArtifactPayload,
    NexonUnionChampionPayload,
    NexonUnionPayload,
)
from app.models.notice import NoticeFeed, NoticeItem
from app.models.ranking import CharacterRanking
from app.models.union import UnionArtifactEffect, UnionChampion, UnionOverview


_KST = timezone(timedelta(hours=9))
_RESPONSE_ERROR_MESSAGE = "NEXON API 응답을 해석하지 못했습니다."
_UNAVAILABLE_MESSAGE = "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
ModelT = TypeVar("ModelT", bound=BaseModel)
NowProvider = Callable[[], datetime]


@dataclass(slots=True, frozen=True)
class NexonMapleClientConfig:
    base_url: str = "https://open.api.nexon.com"
    character_id_path: str = "/maplestory/v1/id"
    character_basic_path: str = "/maplestory/v1/character/basic"
    character_hexa_path: str = "/maplestory/v1/character/hexamatrix"
    character_hexa_stat_path: str = "/maplestory/v1/character/hexamatrix-stat"
    union_path: str = "/maplestory/v1/user/union"
    union_artifact_path: str = "/maplestory/v1/user/union-artifact"
    union_champion_path: str = "/maplestory/v1/user/union-champion"
    ranking_overall_path: str = "/maplestory/v1/ranking/overall"
    notice_path: str = "/maplestory/v1/notice"
    history_window_days: int = 10
    history_max_concurrency: int = 4
    ranking_fallback_days: int = 2


class NexonMapleClient:
    def __init__(
        self,
        *,
        http_client_manager: HttpClientManager,
        api_key: str | None,
        config: NexonMapleClientConfig | None = None,
        now_provider: NowProvider | None = None,
    ) -> None:
        self._http_client_manager = http_client_manager
        self._api_key = api_key
        self._config = config or NexonMapleClientConfig()
        self._now_provider = now_provider or (lambda: datetime.now(tz=_KST))

    async def resolve_ocid(self, character_name: str) -> str:
        payload = await self._get_model(
            self._config.character_id_path,
            params={"character_name": character_name},
            model_type=NexonCharacterIdentifierPayload,
            bad_request_error=CharacterNotFoundError("캐릭터를 찾을 수 없습니다."),
        )
        return payload.ocid

    async def fetch_hexa_overview(self, character_name: str) -> HexaOverview:
        ocid = await self.resolve_ocid(character_name)
        hexa_payload, hexa_stat_payload = await asyncio.gather(
            self._get_model(
                self._config.character_hexa_path,
                params={"ocid": ocid},
                model_type=NexonCharacterHexaPayload,
                allow_missing=True,
            ),
            self._get_model(
                self._config.character_hexa_stat_path,
                params={"ocid": ocid},
                model_type=NexonCharacterHexaStatPayload,
                allow_missing=True,
            ),
        )

        cores = self._build_hexa_cores(hexa_payload)
        stat_sets = self._build_hexa_stat_sets(hexa_stat_payload)
        if not cores and not any(stat_set.cores for stat_set in stat_sets):
            raise EmptyHexaError("HEXA 정보가 없습니다.")

        return HexaOverview(
            character_name=character_name,
            cores=cores,
            stat_sets=stat_sets,
        )

    async def fetch_union_overview(self, character_name: str) -> UnionOverview:
        ocid = await self.resolve_ocid(character_name)
        union_payload, artifact_payload, champion_payload = await asyncio.gather(
            self._get_model(
                self._config.union_path,
                params={"ocid": ocid},
                model_type=NexonUnionPayload,
                allow_missing=True,
            ),
            self._get_model(
                self._config.union_artifact_path,
                params={"ocid": ocid},
                model_type=NexonUnionArtifactPayload,
                allow_missing=True,
            ),
            self._get_model(
                self._config.union_champion_path,
                params={"ocid": ocid},
                model_type=NexonUnionChampionPayload,
                allow_missing=True,
            ),
        )

        if union_payload is None or self._is_empty_union_payload(union_payload):
            raise EmptyUnionError("유니온 정보가 없습니다.")

        return UnionOverview(
            character_name=character_name,
            union_level=union_payload.union_level,
            union_grade=union_payload.union_grade,
            union_artifact_level=union_payload.union_artifact_level,
            union_artifact_exp=union_payload.union_artifact_exp,
            union_artifact_point=union_payload.union_artifact_point,
            union_artifact_remain_ap=(
                None if artifact_payload is None else artifact_payload.union_artifact_remain_ap
            ),
            artifact_effects=(
                []
                if artifact_payload is None
                else [
                    UnionArtifactEffect(name=effect.name, level=effect.level)
                    for effect in artifact_payload.union_artifact_effect
                ]
            ),
            champions=(
                []
                if champion_payload is None
                else [
                    UnionChampion(
                        name=champion.champion_name,
                        class_name=champion.champion_class,
                        grade=champion.champion_grade,
                        badge_effects=[badge.stat for badge in champion.champion_badge_info],
                    )
                    for champion in champion_payload.union_champion
                ]
            ),
            champion_badge_totals=(
                []
                if champion_payload is None
                else [badge.stat for badge in champion_payload.champion_badge_total_info]
            ),
        )

    async def fetch_overall_ranking(self, character_name: str) -> CharacterRanking:
        ocid = await self.resolve_ocid(character_name)
        for target_date in self._ranking_candidate_dates():
            payload = await self._get_model(
                self._config.ranking_overall_path,
                params={
                    "date": target_date.isoformat(),
                    "ocid": ocid,
                },
                model_type=NexonOverallRankingPayload,
                allow_missing=True,
            )
            if payload is None or not payload.ranking:
                continue

            entry = payload.ranking[0]
            return CharacterRanking(
                character_name=entry.character_name,
                ranking=entry.ranking,
                ranking_date=entry.date,
                world_name=entry.world_name,
                class_name=entry.class_name,
                sub_class_name=entry.sub_class_name,
                character_level=entry.character_level,
            )

        raise RankingUnavailableError("현재 랭킹 정보를 확인할 수 없습니다.")

    async def fetch_latest_notices(self, *, limit: int = 5) -> NoticeFeed:
        payload = await self._get_model(
            self._config.notice_path,
            params={},
            model_type=NexonNoticePayload,
        )
        items = sorted(payload.notice, key=lambda item: item.date, reverse=True)
        if not items:
            raise EmptyNoticeError("공지 정보가 없습니다.")

        return NoticeFeed(
            items=[
                NoticeItem(title=item.title, url=item.url, published_at=item.date)
                for item in items[:limit]
            ]
        )

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        ocid = await self.resolve_ocid(character_name)
        candidate_dates = self._history_candidate_dates()
        semaphore = asyncio.Semaphore(self._config.history_max_concurrency)

        async def fetch_snapshot(target_date: date) -> NexonCharacterBasicPayload | None:
            async with semaphore:
                return await self._get_model(
                    self._config.character_basic_path,
                    params={
                        "ocid": ocid,
                        "date": target_date.isoformat(),
                    },
                    model_type=NexonCharacterBasicPayload,
                    allow_missing=True,
                )

        payloads = await asyncio.gather(*(fetch_snapshot(target_date) for target_date in candidate_dates))
        available_payloads = [payload for payload in payloads if payload is not None]
        if not available_payloads:
            raise EmptyHistoryError("경험치 히스토리가 없습니다.")

        entries = [
            ExperienceHistoryEntry(
                date=snapshot_at.date(),
                snapshot_at=snapshot_at,
                level=payload.character_level,
                experience=payload.character_exp,
                experience_percent=payload.character_exp_rate,
            )
            for payload in available_payloads
            for snapshot_at in [payload.date.astimezone(_KST)]
        ]
        entries.sort(
            key=lambda entry: (
                self._normalized_snapshot_at(entry.snapshot_at),
                entry.level,
                entry.experience,
            )
        )
        world_name = next((payload.world_name for payload in available_payloads if payload.world_name), None)
        return ExperienceHistory(
            character_name=character_name,
            world_name=world_name,
            entries=entries,
        )

    async def _get_model(
        self,
        path: str,
        *,
        params: dict[str, str],
        model_type: type[ModelT],
        allow_missing: bool = False,
        bad_request_error: CrawlerError | None = None,
    ) -> ModelT | None:
        payload = await self._request_json(
            path,
            params=params,
            allow_missing=allow_missing,
            bad_request_error=bad_request_error,
        )
        if payload is None:
            return None

        try:
            return model_type.model_validate(payload)
        except ValidationError as exc:
            raise CrawlerError(_RESPONSE_ERROR_MESSAGE) from exc

    async def _request_json(
        self,
        path: str,
        *,
        params: dict[str, str],
        allow_missing: bool,
        bad_request_error: CrawlerError | None,
    ) -> Any | None:
        try:
            response = await self._http_client_manager.client.get(
                f"{self._config.base_url}{path}",
                params=params,
                headers=self._build_headers(),
            )
        except httpx.TimeoutException as exc:
            raise ExternalSiteUnavailableError(_UNAVAILABLE_MESSAGE) from exc
        except httpx.RequestError as exc:
            raise ExternalSiteUnavailableError(_UNAVAILABLE_MESSAGE) from exc

        if response.status_code in {401, 403}:
            raise ConfigurationError("현재 NEXON API 설정이 올바르지 않습니다.")

        if response.status_code == 400:
            if bad_request_error is not None:
                raise bad_request_error
            if allow_missing:
                return None
            raise CrawlerError("NEXON API 요청에 실패했습니다.")

        if response.status_code == 404 and allow_missing:
            return None

        if response.status_code == 429 or response.status_code >= 500:
            raise ExternalSiteUnavailableError(_UNAVAILABLE_MESSAGE)

        if response.is_error:
            raise CrawlerError("NEXON API 요청에 실패했습니다.")

        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            raise CrawlerError(_RESPONSE_ERROR_MESSAGE)

        try:
            return response.json()
        except ValueError as exc:
            raise CrawlerError(_RESPONSE_ERROR_MESSAGE) from exc

    def _build_headers(self) -> dict[str, str]:
        if self._api_key is None:
            raise ConfigurationError("NEXON API 키 설정이 필요합니다.")
        return {"x-nxopen-api-key": self._api_key}

    def _history_candidate_dates(self) -> list[date]:
        today = self._kst_now().date()
        return [today - timedelta(days=offset) for offset in range(self._config.history_window_days)]

    def _ranking_candidate_dates(self) -> list[date]:
        today = self._kst_now().date()
        return [today - timedelta(days=offset) for offset in range(self._config.ranking_fallback_days)]

    def _kst_now(self) -> datetime:
        current = self._now_provider()
        if current.tzinfo is None:
            return current.replace(tzinfo=_KST)
        return current.astimezone(_KST)

    @staticmethod
    def _build_hexa_cores(payload: NexonCharacterHexaPayload | None) -> list[HexaCore]:
        if payload is None:
            return []

        return [
            HexaCore(
                name=core.hexa_core_name,
                level=core.hexa_core_level,
                core_type=core.hexa_core_type,
                linked_skills=[skill.hexa_skill_id for skill in core.linked_skill],
            )
            for core in payload.character_hexa_core_equipment
        ]

    @staticmethod
    def _build_hexa_stat_sets(payload: NexonCharacterHexaStatPayload | None) -> list[HexaStatSet]:
        if payload is None:
            return []

        stat_sets = [
            HexaStatSet(
                label="HEXA 스탯 I",
                cores=NexonMapleClient._map_hexa_stat_cores(payload.character_hexa_stat_core),
            ),
            HexaStatSet(
                label="HEXA 스탯 II",
                cores=NexonMapleClient._map_hexa_stat_cores(payload.character_hexa_stat_core_2),
            ),
            HexaStatSet(
                label="HEXA 스탯 III",
                cores=NexonMapleClient._map_hexa_stat_cores(payload.character_hexa_stat_core_3),
            ),
        ]
        return [stat_set for stat_set in stat_sets if stat_set.cores]

    @staticmethod
    def _map_hexa_stat_cores(payloads: Sequence[NexonHexaStatCorePayload]) -> list[HexaStatCore]:
        return [
            HexaStatCore(
                slot_id=payload.slot_id,
                main_stat_name=payload.main_stat_name,
                main_stat_level=payload.main_stat_level,
                sub_stat_name_1=payload.sub_stat_name_1,
                sub_stat_level_1=payload.sub_stat_level_1,
                sub_stat_name_2=payload.sub_stat_name_2,
                sub_stat_level_2=payload.sub_stat_level_2,
                stat_grade=payload.stat_grade,
            )
            for payload in payloads
        ]

    @staticmethod
    def _is_empty_union_payload(payload: NexonUnionPayload) -> bool:
        return payload.union_level <= 0 and not payload.union_grade

    @staticmethod
    def _normalized_snapshot_at(snapshot_at: datetime | None) -> datetime:
        if snapshot_at is None:
            return datetime(1970, 1, 1, tzinfo=_KST)
        if snapshot_at.tzinfo is None:
            return snapshot_at.replace(tzinfo=_KST)
        return snapshot_at.astimezone(_KST)
