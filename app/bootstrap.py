from __future__ import annotations

from dataclasses import dataclass

from app.clients.nexon_maple import NexonMapleClient
from app.commands.converted_stat import ConvertedStatCommand
from app.commands.experience_history import ExperienceHistoryCommand
from app.commands.hexa import HexaCommand
from app.commands.hexa_cost import HexaCostCommand
from app.commands.notice import NoticeCommand
from app.commands.ranking import RankingCommand
from app.commands.router import CommandRouter
from app.commands.union import UnionCommand
from app.core.http_client import HttpClientManager
from app.core.settings import ApplicationSettings
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
    nexon_maple_client: NexonMapleClient | None = None,
) -> ApplicationServices:
    application_settings = settings or ApplicationSettings.from_env()
    link_builder = maple_scouter_link_builder or MapleScouterLinkBuilder()
    client_manager = http_client_manager or HttpClientManager(
        settings=application_settings.http_client_settings,
    )
    provider_client = nexon_maple_client or NexonMapleClient(
        http_client_manager=client_manager,
        api_key=application_settings.nexon_api_key,
    )
    command_router = CommandRouter(
        handlers=[
            ConvertedStatCommand(link_builder),
            HexaCommand(provider_client),
            HexaCostCommand(),
            UnionCommand(provider_client),
            RankingCommand(provider_client),
            NoticeCommand(provider_client),
            ExperienceHistoryCommand(provider_client),
        ]
    )
    return ApplicationServices(
        http_client_manager=client_manager,
        command_router=command_router,
    )