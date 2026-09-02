from __future__ import annotations

import asyncio

import pytest

from app.commands.union import UnionCommand
from app.core.exceptions import CharacterNotFoundError, EmptyUnionError, ExternalSiteUnavailableError
from app.models.command import ParsedCommand
from app.models.union import UnionArtifactEffect, UnionChampion, UnionOverview


class FakeUnionReader:
    def __init__(self, overview: UnionOverview | None = None, *, error: Exception | None = None) -> None:
        self.overview = overview
        self.error = error
        self.received_names: list[str] = []

    async def fetch_union_overview(self, character_name: str) -> UnionOverview:
        self.received_names.append(character_name)
        if self.error is not None:
            raise self.error
        assert self.overview is not None
        return self.overview


def test_union_command_formats_verified_summary_information() -> None:
    reader = FakeUnionReader(
        UnionOverview(
            character_name="창킬",
            union_level=9867,
            union_grade="그랜드 마스터 유니온 4",
            union_artifact_level=59,
            union_artifact_point=19700,
            union_artifact_remain_ap=6,
            artifact_effects=[
                UnionArtifactEffect(name="올스탯 150 증가", level=10),
                UnionArtifactEffect(name="공격력 30, 마력 30 증가", level=10),
                UnionArtifactEffect(name="데미지 15.00% 증가", level=10),
                UnionArtifactEffect(name="보스 몬스터 공격 시 데미지 15.00% 증가", level=10),
                UnionArtifactEffect(name="몬스터 방어율 무시 20% 증가", level=10),
            ],
            champions=[
                UnionChampion(name="대표캐릭터", grade="SSS"),
                UnionChampion(name="부캐A", grade="SS"),
                UnionChampion(name="부캐B", grade="SS"),
                UnionChampion(name="부캐C", grade="C"),
            ],
            champion_badge_totals=[
                "올스탯 80, 최대 HP/MP 4000 증가",
                "공격력/마력 40 증가",
                "보스 몬스터 공격 시 데미지 20% 증가",
                "크리티컬 데미지 12.00% 증가",
                "방어율 무시 5% 증가",
            ],
        )
    )
    command = UnionCommand(reader)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!유니온 창킬",
                command="유니온",
                character_name="창킬",
            )
        )
    )

    assert reader.received_names == ["창킬"]
    assert result == (
        "[창킬 유니온]\n\n"
        "유니온 레벨: 9,867\n"
        "유니온 등급: 그랜드 마스터 유니온 4\n"
        "아티팩트 레벨: 59\n"
        "아티팩트 포인트: 19,700\n"
        "잔여 아티팩트 AP: 6\n"
        "아티팩트 효과: 올스탯 150 증가 / 공격력 30, 마력 30 증가 / 데미지 15.00% 증가 / 보스 몬스터 공격 시 데미지 15.00% 증가 외 1개\n\n"
        "유니온 챔피언\n"
        "SSS: 1명\n"
        "SS: 2명\n"
        "C: 1명\n"
        "누적 효과: 올스탯 80, 최대 HP/MP 4000 증가 / 공격력/마력 40 증가 / 보스 몬스터 공격 시 데미지 20% 증가 / 크리티컬 데미지 12.00% 증가 외 1개"
    )


def test_union_command_propagates_empty_provider_data() -> None:
    command = UnionCommand(FakeUnionReader(error=EmptyUnionError("유니온 정보가 없습니다.")))

    with pytest.raises(EmptyUnionError, match="유니온 정보가 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!유니온 창킬",
                    command="유니온",
                    character_name="창킬",
                )
            )
        )


def test_union_command_propagates_character_not_found() -> None:
    command = UnionCommand(FakeUnionReader(error=CharacterNotFoundError("캐릭터를 찾을 수 없습니다.")))

    with pytest.raises(CharacterNotFoundError, match="캐릭터를 찾을 수 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!유니온 창킬",
                    command="유니온",
                    character_name="창킬",
                )
            )
        )


def test_union_command_propagates_provider_unavailable() -> None:
    command = UnionCommand(
        FakeUnionReader(
            error=ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            )
        )
    )

    with pytest.raises(ExternalSiteUnavailableError, match="현재 조회 사이트에 접속할 수 없습니다."):
        asyncio.run(
            command.handle(
                ParsedCommand(
                    raw_text="!유니온 창킬",
                    command="유니온",
                    character_name="창킬",
                )
            )
        )
