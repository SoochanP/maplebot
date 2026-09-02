from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import httpx

from app.bootstrap import ApplicationServices
from app.commands.converted_stat import ConvertedStatCommand
from app.commands.experience_history import ExperienceHistoryCommand
from app.commands.hexa import HexaCommand
from app.commands.hexa_cost import HexaCostCommand
from app.commands.notice import NoticeCommand
from app.commands.ranking import RankingCommand
from app.commands.router import CommandRouter
from app.commands.union import UnionCommand
from app.core.exceptions import ExternalSiteUnavailableError
from app.core.http_client import HttpClientManager, HttpClientSettings
from app.core.settings import ApplicationSettings
from app.main import create_app
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry
from app.models.hexa import HexaCore, HexaOverview, HexaStatCore, HexaStatSet
from app.models.notice import NoticeFeed, NoticeItem
from app.models.ranking import CharacterRanking
from app.models.union import UnionArtifactEffect, UnionChampion, UnionOverview
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
        self.hexa_received_names: list[str] = []
        self.union_received_names: list[str] = []
        self.ranking_received_names: list[str] = []
        self.notice_limits: list[int] = []

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        self.received_names.append(character_name)

        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        if self._error is not None:
            raise self._error

        return ExperienceHistory(
            character_name=character_name,
            world_name="\uc2a4\uce74\ub2c8\uc544",
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

    async def fetch_hexa_overview(self, character_name: str) -> HexaOverview:
        self.hexa_received_names.append(character_name)
        return HexaOverview(
            character_name=character_name,
            cores=[
                HexaCore(
                    name="\ub370\ub4dc \uc2a4\ud398\uc774\uc2a4",
                    level=18,
                    core_type="\uc2a4\ud0ac \ucf54\uc5b4",
                    linked_skills=["\ub370\ub4dc \uc2a4\ud398\uc774\uc2a4"],
                )
            ],
            stat_sets=[
                HexaStatSet(
                    label="HEXA \uc2a4\ud0ef I",
                    cores=[
                        HexaStatCore(
                            main_stat_name="\uacf5\uaca9\ub825 \uc99d\uac00",
                            main_stat_level=8,
                        )
                    ],
                )
            ],
        )

    async def fetch_union_overview(self, character_name: str) -> UnionOverview:
        self.union_received_names.append(character_name)
        return UnionOverview(
            character_name=character_name,
            union_level=9867,
            union_grade="\uadf8\ub79c\ub4dc \ub9c8\uc2a4\ud130 \uc720\ub2c8\uc628 4",
            union_artifact_level=59,
            union_artifact_point=19700,
            union_artifact_remain_ap=6,
            artifact_effects=[
                UnionArtifactEffect(name="\uc62c\uc2a4\ud0ef 150 \uc99d\uac00", level=10),
            ],
            champions=[
                UnionChampion(name="\ub300\ud45c\uce90\ub9ad\ud130", grade="SSS"),
            ],
            champion_badge_totals=["\ud06c\ub9ac\ud2f0\uceec \ub370\ubbf8\uc9c0 12.00% \uc99d\uac00"],
        )

    async def fetch_overall_ranking(self, character_name: str) -> CharacterRanking:
        self.ranking_received_names.append(character_name)
        return CharacterRanking(
            character_name=character_name,
            ranking=12345,
            ranking_date=date(2025, 1, 12),
            world_name="\uc2a4\uce74\ub2c8\uc544",
            class_name="\ub2e4\ud06c\ub098\uc774\ud2b8",
            character_level=289,
        )

    async def fetch_latest_notices(self, *, limit: int = 5) -> NoticeFeed:
        self.notice_limits.append(limit)
        return NoticeFeed(
            items=[
                NoticeItem(
                    title="\ud14c\uc2a4\ud2b8 \uacf5\uc9c0",
                    url="https://example.com/notices/1",
                    published_at=datetime(2025, 1, 12, tzinfo=timezone.utc),
                )
            ]
        )


def build_test_app(
    *,
    kakao_skill_token: str | None = None,
    bridge_token: str | None = None,
    kakao_request_timeout_seconds: float = 4.5,
    command_execution_timeout_seconds: float = 15.0,
    http_request_timeout_seconds: float = 8.0,
    http_connect_timeout_seconds: float = 2.0,
    history_crawler: FakeHistoryCrawler | None = None,
) -> tuple[Any, FakeHistoryCrawler]:
    crawler = history_crawler or FakeHistoryCrawler()
    services = ApplicationServices(
        http_client_manager=HttpClientManager(
            settings=HttpClientSettings(
                request_timeout_seconds=http_request_timeout_seconds,
                connect_timeout_seconds=http_connect_timeout_seconds,
            )
        ),
        command_router=CommandRouter(
            handlers=[
                ConvertedStatCommand(MapleScouterLinkBuilder()),
                HexaCommand(crawler),
                HexaCostCommand(),
                UnionCommand(crawler),
                RankingCommand(crawler),
                NoticeCommand(crawler),
                ExperienceHistoryCommand(crawler),
            ]
        ),
    )
    settings = ApplicationSettings(
        kakao_skill_token=kakao_skill_token,
        bridge_token=bridge_token,
        kakao_request_timeout_seconds=kakao_request_timeout_seconds,
        command_execution_timeout_seconds=command_execution_timeout_seconds,
        http_request_timeout_seconds=http_request_timeout_seconds,
        http_connect_timeout_seconds=http_connect_timeout_seconds,
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
        "\ud604\uc7ac \uc870\ud68c \uc0ac\uc774\ud2b8\uc5d0 \uc811\uc18d\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
    )