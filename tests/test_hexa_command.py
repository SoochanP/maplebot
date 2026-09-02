from __future__ import annotations

import asyncio

import pytest

from app.commands.hexa import HexaCommand
from app.core.exceptions import CharacterNotFoundError, EmptyHexaError, ExternalSiteUnavailableError
from app.models.command import ParsedCommand
from app.models.hexa import HexaCore, HexaOverview, HexaStatCore, HexaStatSet


class FakeHexaReader:
    def __init__(self, overview: HexaOverview | None = None, *, error: Exception | None = None) -> None:
        self.overview = overview
        self.error = error
        self.received_names: list[str] = []

    async def fetch_hexa_overview(self, character_name: str) -> HexaOverview:
        self.received_names.append(character_name)
        if self.error is not None:
            raise self.error
        assert self.overview is not None
        return self.overview


def test_hexa_command_formats_grouped_core_and_stat_sections() -> None:
    reader = FakeHexaReader(
        HexaOverview(
            character_name="창킬",
            cores=[
                HexaCore(
                    name="데드 스페이스",
                    level=18,
                    core_type="스킬 코어",
                    linked_skills=["데드 스페이스"],
                ),
                HexaCore(
                    name="다크 임페일 VI/다크 신서시스 VI",
                    level=30,
                    core_type="마스터리 코어",
                    linked_skills=["다크 임페일 VI", "다크 신서시스 VI"],
                ),
                HexaCore(
                    name="솔 야누스",
                    level=30,
                    core_type="공용 코어",
                    linked_skills=["솔 야누스", "솔 야누스 : 새벽", "솔 야누스 : 황혼"],
                ),
            ],
            stat_sets=[
                HexaStatSet(
                    label="HEXA 스탯 I",
                    cores=[
                        HexaStatCore(
                            main_stat_name="공격력 증가",
                            main_stat_level=8,
                            sub_stat_name_1="주력 스탯 증가",
                            sub_stat_level_1=6,
                            sub_stat_name_2="크리티컬 데미지 증가",
                            sub_stat_level_2=6,
                        )
                    ],
                ),
                HexaStatSet(
                    label="HEXA 스탯 II",
                    cores=[
                        HexaStatCore(
                            main_stat_name="주력 스탯 증가",
                            main_stat_level=5,
                            sub_stat_name_1="크리티컬 데미지 증가",
                            sub_stat_level_1=6,
                            sub_stat_name_2="공격력 증가",
                            sub_stat_level_2=9,
                        )
                    ],
                ),
            ],
        )
    )
    command = HexaCommand(reader)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!헥사 창킬",
                command="헥사",
                character_name="창킬",
            )
        )
    )

    assert reader.received_names == ["창킬"]
    assert result == (
        "[창킬 HEXA]\n\n"
        "HEXA 코어\n"
        "[스킬 코어]\n"
        "- 데드 스페이스 Lv.18\n\n"
        "[마스터리 코어]\n"
        "- 다크 임페일 VI/다크 신서시스 VI Lv.30\n"
        "  연결 스킬: 다크 임페일 VI, 다크 신서시스 VI\n\n"
        "[공용 코어]\n"
        "- 솔 야누스 Lv.30\n"
        "  연결 스킬: 솔 야누스, 솔 야누스 : 새벽, 솔 야누스 : 황혼\n\n"
        "HEXA 스탯\n"
        "- I: 공격력 증가 Lv.8 / 주력 스탯 증가 Lv.6 / 크리티컬 데미지 증가 Lv.6\n"
        "- II: 주력 스탯 증가 Lv.5 / 크리티컬 데미지 증가 Lv.6 / 공격력 증가 Lv.9"
    )


def test_hexa_command_propagates_empty_provider_data() -> None:
    command = HexaCommand(FakeHexaReader(error=EmptyHexaError("HEXA 정보가 없습니다.")))

    with pytest.raises(EmptyHexaError, match="HEXA 정보가 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!헥사 창킬",
                    command="헥사",
                    character_name="창킬",
                )
            )
        )


def test_hexa_command_propagates_character_not_found() -> None:
    command = HexaCommand(FakeHexaReader(error=CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")))

    with pytest.raises(CharacterNotFoundError, match="캐릭터를 찾을 수 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!헥사 창킬",
                    command="헥사",
                    character_name="창킬",
                )
            )
        )


def test_hexa_command_propagates_provider_unavailable() -> None:
    command = HexaCommand(
        FakeHexaReader(
            error=ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            )
        )
    )

    with pytest.raises(ExternalSiteUnavailableError, match="현재 조회 사이트에 접속할 수 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!헥사 창킬",
                    command="헥사",
                    character_name="창킬",
                )
            )
        )
