from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.bootstrap import ApplicationServices
from app.commands.converted_stat import ConvertedStatCommand
from app.commands.experience_history import ExperienceHistoryCommand
from app.commands.router import CommandRouter
from app.core.exceptions import ExternalSiteUnavailableError
from app.core.http_client import HttpClientManager, HttpClientSettings
from app.core.settings import ApplicationSettings
from app.main import create_app
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry
from app.services.maple_scouter_link import MapleScouterLinkBuilder


class FakeHistoryCrawler:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._error = error
        self._delay_seconds = delay_seconds
        self.received_names: list[str] = []

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        self.received_names.append(character_name)

        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        if self._error is not None:
            raise self._error

        return ExperienceHistory(
            character_name=character_name,
            entries=[
                ExperienceHistoryEntry(
                    date=date(2025, 1, 11),
                    snapshot_at=datetime(2025, 1, 11, tzinfo=timezone.utc),
                    level=289,
                    experience=1000,
                    experience_percent=Decimal("10.000"),
                ),
                ExperienceHistoryEntry(
                    date=date(2025, 1, 12),
                    snapshot_at=datetime(2025, 1, 12, tzinfo=timezone.utc),
                    level=289,
                    experience=1250,
                    experience_percent=Decimal("12.500"),
                ),
            ],
        )


def build_test_app(
    *,
    kakao_skill_token: str | None = None,
    bridge_token: str | None = None,
    kakao_request_timeout_seconds: float = 4.5,
    history_crawler: FakeHistoryCrawler | None = None,
) -> tuple[Any, FakeHistoryCrawler]:
    crawler = history_crawler or FakeHistoryCrawler()
    services = ApplicationServices(
        http_client_manager=HttpClientManager(settings=HttpClientSettings()),
        command_router=CommandRouter(
            handlers=[
                ConvertedStatCommand(MapleScouterLinkBuilder()),
                ExperienceHistoryCommand(crawler),
            ]
        ),
    )
    settings = ApplicationSettings(
        kakao_skill_token=kakao_skill_token,
        bridge_token=bridge_token,
        kakao_request_timeout_seconds=kakao_request_timeout_seconds,
    )
    app = create_app(services=services, settings=settings)
    return app, crawler


def request_json(
    app: Any,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json: object | None = None,
) -> httpx.Response:
    async def run_request() -> httpx.Response:
        services = app.state.services
        await services.start()
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(
                    method,
                    path,
                    headers=headers,
                    json=json,
                )
        finally:
            await services.close()

    return asyncio.run(run_request())


def build_provider_timeout_error() -> ExternalSiteUnavailableError:
    return ExternalSiteUnavailableError(
        "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
    )
