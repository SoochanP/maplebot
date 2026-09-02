from __future__ import annotations

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.services.maple_scouter_link import MapleScouterLinkBuilder


class ConvertedStatCommand(CommandHandler):
    command_name = "환산"

    def __init__(self, link_builder: MapleScouterLinkBuilder) -> None:
        self._link_builder = link_builder

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        url = self._link_builder.build(character_name)
        return self._format_response(character_name, url)

    @staticmethod
    def _format_response(character_name: str, url: str) -> str:
        return f"[{character_name} 환산주스탯]\n\n{url}"
