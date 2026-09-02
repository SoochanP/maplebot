from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Protocol

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.models.hexa import HexaCore, HexaOverview, HexaStatCore, HexaStatSet


class HexaReader(Protocol):
    async def fetch_hexa_overview(self, character_name: str) -> HexaOverview:
        ...


class HexaCommand(CommandHandler):
    command_name = "헥사"

    _CORE_TYPE_ORDER = {
        "스킬 코어": 0,
        "마스터리 코어": 1,
        "강화 코어": 2,
        "공용 코어": 3,
    }

    def __init__(self, reader: HexaReader) -> None:
        self._reader = reader

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        overview = await self._reader.fetch_hexa_overview(character_name)
        return self._format_response(overview)

    def _format_response(self, overview: HexaOverview) -> str:
        sections = [f"[{overview.character_name} HEXA]"]

        if overview.cores:
            core_sections = ["HEXA 코어"]
            for core_type, cores in self._group_cores(overview.cores):
                core_sections.append(f"[{core_type}]")
                for core in cores:
                    core_sections.extend(self._format_core_lines(core))
                core_sections.append("")
            if core_sections[-1] == "":
                core_sections.pop()
            sections.append("\n".join(core_sections))

        if overview.stat_sets:
            stat_lines = ["HEXA 스탯"]
            for stat_set in overview.stat_sets:
                stat_lines.extend(self._format_stat_set_lines(stat_set))
            sections.append("\n".join(stat_lines))

        return "\n\n".join(sections)

    def _group_cores(self, cores: Iterable[HexaCore]) -> list[tuple[str, list[HexaCore]]]:
        grouped: dict[str, list[HexaCore]] = defaultdict(list)
        for core in cores:
            grouped[core.core_type or "기타 코어"].append(core)

        return sorted(
            grouped.items(),
            key=lambda item: (self._CORE_TYPE_ORDER.get(item[0], 99), item[0]),
        )

    def _format_core_lines(self, core: HexaCore) -> list[str]:
        lines = [f"- {core.name} Lv.{core.level}"]
        if self._should_show_linked_skills(core):
            lines.append(f"  연결 스킬: {', '.join(core.linked_skills)}")
        return lines

    @staticmethod
    def _should_show_linked_skills(core: HexaCore) -> bool:
        if not core.linked_skills:
            return False
        if len(core.linked_skills) > 1:
            return True
        return core.linked_skills[0] != core.name

    def _format_stat_set_lines(self, stat_set: HexaStatSet) -> list[str]:
        lines: list[str] = []
        label = stat_set.label.replace("HEXA 스탯 ", "")
        for core in stat_set.cores:
            lines.append(f"- {label}: {self._format_stat_core(core)}")
        return lines

    @staticmethod
    def _format_stat_core(core: HexaStatCore) -> str:
        parts: list[str] = []
        for stat_name, stat_level in (
            (core.main_stat_name, core.main_stat_level),
            (core.sub_stat_name_1, core.sub_stat_level_1),
            (core.sub_stat_name_2, core.sub_stat_level_2),
        ):
            if stat_name is None:
                continue
            if stat_level is None:
                parts.append(stat_name)
            else:
                parts.append(f"{stat_name} Lv.{stat_level}")
        return " / ".join(parts) if parts else "설정 정보 없음"
