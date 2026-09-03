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


def test_hexa_command_formats_compact_core_list_and_cumulative_cost() -> None:
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
                    name="다크 스피어",
                    level=30,
                    core_type="강화 코어",
                    linked_skills=["다크 스피어 강화"],
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
                        )
                    ],
                )
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
        "[창킬] 헥사 스킬 정보\n\n"
        "• [스킬] Lv.18 데드 스페이스\n"
        "• [마스] Lv.30 다크 임페일 VI/다크 신서시스 VI\n"
        "• [강화] Lv.30 다크 스피어\n"
        "• [공용] Lv.30 솔 야누스\n\n"
        "• 누적 솔 에르다 : 474 / 564 (84%)\n"
        "• 누적 조각 : 13,403 / 16,403 (81%)"
    )
    assert "연결 스킬" not in result
    assert "HEXA 스탯" not in result


def test_hexa_command_uses_existing_skill_cost_for_unregistered_skill_core() -> None:
    reader = FakeHexaReader(
        HexaOverview(
            character_name="창킬",
            cores=[
                HexaCore(
                    name="미등록 헥사 코어",
                    level=12,
                    core_type="스킬 코어",
                    linked_skills=["미등록 헥사 코어"],
                )
            ],
            stat_sets=[
                HexaStatSet(
                    label="HEXA 스탯 I",
                    cores=[HexaStatCore(main_stat_name="공격력 증가", main_stat_level=8)],
                )
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

    assert result == (
        "[창킬] 헥사 스킬 정보\n\n"
        "• [스킬] Lv.12 미등록 헥사 코어\n\n"
        "• 누적 솔 에르다 : 41 / 150 (27%)\n"
        "• 누적 조각 : 850 / 4,500 (18%)"
    )
    assert "HEXA 스탯" not in result


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
