from __future__ import annotations

from collections import Counter
from typing import Protocol

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.models.union import UnionArtifactEffect, UnionOverview


class UnionReader(Protocol):
    async def fetch_union_overview(self, character_name: str) -> UnionOverview:
        ...


class UnionCommand(CommandHandler):
    command_name = "유니온"

    _GRADE_ORDER = {
        "SSS": 0,
        "SS": 1,
        "S": 2,
        "A": 3,
        "B": 4,
        "C": 5,
    }

    def __init__(
        self,
        reader: UnionReader,
        *,
        artifact_effect_display_limit: int = 4,
        badge_effect_display_limit: int = 4,
    ) -> None:
        self._reader = reader
        self._artifact_effect_display_limit = artifact_effect_display_limit
        self._badge_effect_display_limit = badge_effect_display_limit

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        overview = await self._reader.fetch_union_overview(character_name)
        return self._format_response(overview)

    def _format_response(self, overview: UnionOverview) -> str:
        lines = [f"[{overview.character_name} 유니온]", ""]
        lines.append(f"유니온 레벨: {overview.union_level:,}")

        if overview.union_grade:
            lines.append(f"유니온 등급: {overview.union_grade}")
        if overview.union_artifact_level is not None:
            lines.append(f"아티팩트 레벨: {overview.union_artifact_level:,}")
        if overview.union_artifact_point is not None:
            lines.append(f"아티팩트 포인트: {overview.union_artifact_point:,}")
        if overview.union_artifact_remain_ap is not None:
            lines.append(f"잔여 아티팩트 AP: {overview.union_artifact_remain_ap:,}")
        if overview.artifact_effects:
            lines.append(
                f"아티팩트 효과: {self._format_artifact_effects(overview.artifact_effects)}"
            )

        if overview.champions or overview.champion_badge_totals:
            lines.append("")
            lines.append("유니온 챔피언")
            lines.extend(self._format_champion_grade_lines(overview))
            if overview.champion_badge_totals:
                lines.append(
                    f"누적 효과: {self._format_badge_effects(overview.champion_badge_totals)}"
                )

        return "\n".join(lines)

    def _format_artifact_effects(self, effects: list[UnionArtifactEffect]) -> str:
        visible_effects = [effect.name for effect in effects[: self._artifact_effect_display_limit]]
        return self._join_with_remaining_count(visible_effects, len(effects))

    def _format_champion_grade_lines(self, overview: UnionOverview) -> list[str]:
        if not overview.champions:
            return ["챔피언 정보가 없습니다."]

        counts = Counter(champion.grade or "미확인" for champion in overview.champions)
        sorted_grades = sorted(
            counts.items(),
            key=lambda item: (self._GRADE_ORDER.get(item[0], 99), item[0]),
        )
        return [f"{grade}: {count}명" for grade, count in sorted_grades]

    def _format_badge_effects(self, effects: list[str]) -> str:
        visible_effects = effects[: self._badge_effect_display_limit]
        return self._join_with_remaining_count(visible_effects, len(effects))

    @staticmethod
    def _join_with_remaining_count(items: list[str], total_count: int) -> str:
        text = " / ".join(items)
        remaining_count = total_count - len(items)
        if remaining_count <= 0:
            return text
        return f"{text} 외 {remaining_count}개"
