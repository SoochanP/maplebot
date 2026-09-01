from __future__ import annotations

from dataclasses import dataclass

from app.commands.converted_stat import ConvertedStatCommand
from app.commands.experience_history import ExperienceHistoryCommand
from app.commands.router import CommandRouter
from app.core.http_client import HttpClientManager
from app.core.settings import ApplicationSettings
from app.crawlers.maple_history import MapleHistoryCrawler, MapleHistoryCrawlerConfig
from app.services.maple_scouter_link import MapleScouterLinkBuilder


@dataclass(slots=True)
class ApplicationServices:
    http_client_manager: HttpClientManager
    command_router: CommandRouter

    async def start(self) -> None:
        await self.http_client_manager.start()

    async def close(self) -> None:
        await self.http_client_manager.close()


def build_application_services(
    *,
    settings: ApplicationSettings | None = None,
    maple_scouter_link_builder: MapleScouterLinkBuilder | None = None,
    http_client_manager: HttpClientManager | None = None,
    maple_history_config: MapleHistoryCrawlerConfig | None = None,
) -> ApplicationServices:
    application_settings = settings or ApplicationSettings.from_env()
    link_builder = maple_scouter_link_builder or MapleScouterLinkBuilder()
    client_manager = http_client_manager or HttpClientManager(
        settings=application_settings.http_client_settings,
    )
    maple_history_crawler = MapleHistoryCrawler(
        http_client_manager=client_manager,
        config=maple_history_config or MapleHistoryCrawlerConfig(),
    )
    command_router = CommandRouter(
        handlers=[
            ConvertedStatCommand(link_builder),
            ExperienceHistoryCommand(maple_history_crawler),
        ]
    )
    return ApplicationServices(
        http_client_manager=client_manager,
        command_router=command_router,
    )
