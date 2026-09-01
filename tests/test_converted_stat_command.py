from __future__ import annotations

import asyncio

from app.commands.converted_stat import ConvertedStatCommand
from app.models.command import ParsedCommand


class FakeLinkBuilder:
    def __init__(self, url: str) -> None:
        self.url = url
        self.received_names: list[str] = []

    def build(self, character_name: str) -> str:
        self.received_names.append(character_name)
        return self.url


def test_converted_stat_command_formats_maple_scouter_link_response() -> None:
    link_builder = FakeLinkBuilder(
        "https://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
    )
    command = ConvertedStatCommand(link_builder)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!환산 창킬",
                command="환산",
                character_name="창킬",
            )
        )
    )

    assert link_builder.received_names == ["창킬"]
    assert result == (
        "[창킬 환산주스탯]\n\n"
        "https://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
    )
