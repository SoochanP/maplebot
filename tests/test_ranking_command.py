from __future__ import annotations

import asyncio
from datetime import date

from app.commands.ranking import RankingCommand
from app.models.command import ParsedCommand
from app.models.ranking import CharacterRanking


class FakeRankingReader:
    def __init__(self, ranking: CharacterRanking) -> None:
        self.ranking = ranking
        self.received_names: list[str] = []

    async def fetch_overall_ranking(self, character_name: str) -> CharacterRanking:
        self.received_names.append(character_name)
        return self.ranking


def test_ranking_command_formats_overall_ranking() -> None:
    reader = FakeRankingReader(
        CharacterRanking(
            character_name="창킬",
            ranking=12345,
            ranking_date=date(2026, 9, 1),
            world_name="스카니아",
            class_name="도적",
            sub_class_name="나이트로드",
            character_level=290,
        )
    )
    command = RankingCommand(reader)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!랭킹 창킬",
                command="랭킹",
                character_name="창킬",
            )
        )
    )

    assert reader.received_names == ["창킬"]
    assert result == (
        "[창킬 종합 랭킹]\n\n"
        "기준일: 2026-09-01\n"
        "순위: 12,345위\n"
        "월드: 스카니아\n"
        "직업: 도적 (나이트로드)\n"
        "레벨: 290"
    )
