from __future__ import annotations

from typing import Protocol

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.models.ranking import CharacterRanking


class RankingReader(Protocol):
    async def fetch_overall_ranking(self, character_name: str) -> CharacterRanking:
        ...


class RankingCommand(CommandHandler):
    command_name = "랭킹"

    def __init__(self, reader: RankingReader) -> None:
        self._reader = reader

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        ranking = await self._reader.fetch_overall_ranking(character_name)
        return self._format_response(ranking)

    @staticmethod
    def _format_response(ranking: CharacterRanking) -> str:
        class_name = ranking.class_name or "-"
        if ranking.sub_class_name and ranking.sub_class_name != ranking.class_name:
            class_name = f"{class_name} ({ranking.sub_class_name})"

        lines = [f"[{ranking.character_name} 종합 랭킹]", ""]
        lines.append(f"기준일: {ranking.ranking_date.isoformat()}")
        lines.append(f"순위: {ranking.ranking:,}위")
        if ranking.world_name:
            lines.append(f"월드: {ranking.world_name}")
        lines.append(f"직업: {class_name}")
        if ranking.character_level is not None:
            lines.append(f"레벨: {ranking.character_level:,}")
        return "\n".join(lines)
