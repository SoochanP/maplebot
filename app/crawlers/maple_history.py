from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, ValidationError

from app.core.exceptions import (
    CharacterNotFoundError,
    CrawlerError,
    EmptyHistoryError,
    ExternalSiteUnavailableError,
)
from app.core.http_client import HttpClientManager
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry


_KST = timezone(timedelta(hours=9))


@dataclass(slots=True, frozen=True)
class MapleHistoryCrawlerConfig:
    base_url: str = "https://maplehistory.kr"
    get_characters_path: str = "/ajax/get-characters"
    fetch_characters_path: str = "/ajax/fetch-characters"
    get_character_logs_path: str = "/ajax/get-character-logs"
    pending_codes: frozenset[int] = field(default_factory=lambda: frozenset({101, 102}))
    search_poll_interval_seconds: float = 1.0
    search_poll_attempts: int = 5

    @property
    def headers(self) -> dict[str, str]:
        return {"Accept": "application/json"}


class MapleHistoryCharacterPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    character_name: str
    character_level: int
    character_exp: int
    character_exp_rate: Decimal
    date: int
    removed: int = 0


class MapleHistoryFetchPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: int
    index: int | None = None


class MapleHistoryBasicLogPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    character_id: str
    date: int
    character_name: str
    character_level: int
    character_exp: int
    character_exp_rate: Decimal


class MapleHistoryCrawler:
    def __init__(
        self,
        *,
        http_client_manager: HttpClientManager,
        config: MapleHistoryCrawlerConfig,
    ) -> None:
        self._http_client_manager = http_client_manager
        self._config = config

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        character = await self._resolve_character(character_name)
        logs = await self._get_basic_logs(character.id)
        history = self.parse_experience_history(character.character_name, logs)
        if not history.entries:
            raise EmptyHistoryError("경험치 히스토리가 없습니다.")
        return history

    async def _resolve_character(self, character_name: str) -> MapleHistoryCharacterPayload:
        characters = await self._get_characters_by_name(character_name)
        if not characters:
            await self._fetch_character_by_name(character_name)
            characters = await self._get_characters_by_name(character_name)

        if not characters:
            raise CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")

        sorted_characters = self.sort_characters(characters)
        return sorted_characters[0]

    async def _get_characters_by_name(self, character_name: str) -> list[MapleHistoryCharacterPayload]:
        payload = await self._request_json(
            self._config.get_characters_path,
            params={"name": character_name},
        )
        return self.parse_character_search_payload(payload)

    async def _fetch_character_by_name(self, character_name: str) -> None:
        for attempt in range(self._config.search_poll_attempts):
            payload = await self._request_json(
                self._config.fetch_characters_path,
                params={"name": character_name},
            )
            fetch_result = self.parse_fetch_payload(payload)
            if fetch_result.code not in self._config.pending_codes:
                return
            if attempt < self._config.search_poll_attempts - 1:
                await asyncio.sleep(self._config.search_poll_interval_seconds)

        raise ExternalSiteUnavailableError(
            "조회 사이트 응답이 지연되고 있습니다.\n잠시 후 다시 시도해주세요."
        )

    async def _get_basic_logs(self, character_id: str) -> list[MapleHistoryBasicLogPayload]:
        payload = await self._request_json(
            self._config.get_character_logs_path,
            params={"id": character_id, "name": "basic"},
        )
        return self.parse_basic_log_payload(payload)

    async def _request_json(self, path: str, *, params: dict[str, str]) -> Any:
        try:
            response = await self._http_client_manager.client.get(
                f"{self._config.base_url}{path}",
                params=params,
                headers=self._config.headers,
            )
        except httpx.TimeoutException as exc:
            raise ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            ) from exc
        except httpx.RequestError as exc:
            raise ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            ) from exc

        if response.status_code >= 500:
            raise ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            )

        if response.is_error:
            raise CrawlerError("조회 사이트 요청에 실패했습니다.")

        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type:
            raise CrawlerError("조회 사이트 응답을 해석하지 못했습니다.")

        try:
            return response.json()
        except ValueError as exc:
            raise CrawlerError("조회 사이트 응답을 해석하지 못했습니다.") from exc

    def parse_character_search_payload(self, payload: Any) -> list[MapleHistoryCharacterPayload]:
        if not isinstance(payload, list):
            raise CrawlerError("캐릭터 검색 결과를 해석하지 못했습니다.")

        try:
            return [MapleHistoryCharacterPayload.model_validate(item) for item in payload]
        except ValidationError as exc:
            raise CrawlerError("캐릭터 검색 결과를 해석하지 못했습니다.") from exc

    def parse_fetch_payload(self, payload: Any) -> MapleHistoryFetchPayload:
        try:
            return MapleHistoryFetchPayload.model_validate(payload)
        except ValidationError as exc:
            raise CrawlerError("캐릭터 조회 요청 결과를 해석하지 못했습니다.") from exc

    def parse_basic_log_payload(self, payload: Any) -> list[MapleHistoryBasicLogPayload]:
        if not isinstance(payload, list):
            raise CrawlerError("경험치 히스토리를 해석하지 못했습니다.")

        try:
            logs = [MapleHistoryBasicLogPayload.model_validate(item) for item in payload]
        except ValidationError as exc:
            raise CrawlerError("경험치 히스토리를 해석하지 못했습니다.") from exc

        return sorted(
            logs,
            key=lambda log: (
                log.date,
                log.character_level,
                log.character_exp,
            ),
        )

    def parse_experience_history(
        self,
        character_name: str,
        logs: list[MapleHistoryBasicLogPayload],
    ) -> ExperienceHistory:
        entries = [
            ExperienceHistoryEntry(
                date=self._to_kst_date(log.date),
                snapshot_at=self._to_kst_datetime(log.date),
                level=log.character_level,
                experience=log.character_exp,
                experience_percent=log.character_exp_rate,
            )
            for log in logs
        ]
        return ExperienceHistory(character_name=character_name, entries=entries)

    @staticmethod
    def sort_characters(
        characters: list[MapleHistoryCharacterPayload],
    ) -> list[MapleHistoryCharacterPayload]:
        return sorted(
            characters,
            key=lambda character: (
                character.date,
                character.character_level,
                character.character_exp,
            ),
            reverse=True,
        )

    @staticmethod
    def _to_kst_date(timestamp_ms: int) -> date:
        return MapleHistoryCrawler._to_kst_datetime(timestamp_ms).date()

    @staticmethod
    def _to_kst_datetime(timestamp_ms: int) -> datetime:
        return datetime.fromtimestamp(timestamp_ms / 1000, tz=_KST)
