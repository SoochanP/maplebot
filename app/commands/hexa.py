from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from app.commands.base import CommandHandler
from app.data.hexa_costs import calculate_hexa_cumulative_cost
from app.models.command import ParsedCommand
from app.models.hexa import HexaCore, HexaOverview
from app.models.hexa_cost import HexaCumulativeCostSummary, HexaResourceProgress


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
    _CORE_TYPE_LABELS = {
        "스킬 코어": "스킬",
        "마스터리 코어": "마스",
        "강화 코어": "강화",
        "공용 코어": "공용",
    }
    _COST_UNAVAILABLE_MESSAGE = "계산 불가 (미등록 코어 존재)"

    def __init__(self, reader: HexaReader) -> None:
        self._reader = reader

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        overview = await self._reader.fetch_hexa_overview(character_name)
        return self._format_response(overview)

    def _format_response(self, overview: HexaOverview) -> str:
        sections = [f"[{overview.character_name}] 헥사 스킬 정보"]

        if overview.cores:
            sections.append(
                "\n".join(
                    self._format_core_line(core)
                    for core in self._sort_cores(overview.cores)
                )
            )
            cumulative_lines = self._format_cumulative_lines(
                calculate_hexa_cumulative_cost(overview.cores, overview.stat_sets)
            )
            if cumulative_lines:
                sections.append("\n".join(cumulative_lines))

        return "\n\n".join(sections)

    def _sort_cores(self, cores: Iterable[HexaCore]) -> list[HexaCore]:
        return sorted(
            cores,
            key=lambda core: self._CORE_TYPE_ORDER.get(core.core_type or "", 99),
        )

    def _format_core_line(self, core: HexaCore) -> str:
        return f"• [{self._resolve_core_type_label(core.core_type)}] Lv.{core.level} {core.name}"

    def _resolve_core_type_label(self, core_type: str | None) -> str:
        if core_type is None or not core_type.strip():
            return "기타"
        return self._CORE_TYPE_LABELS.get(core_type, core_type)

    def _format_cumulative_lines(
        self,
        summary: HexaCumulativeCostSummary,
    ) -> list[str]:
        if summary.unresolved_core_names:
            return [
                f"• 누적 솔 에르다 : {self._COST_UNAVAILABLE_MESSAGE}",
                f"• 누적 조각 : {self._COST_UNAVAILABLE_MESSAGE}",
            ]

        if summary.sol_erda is None or summary.fragments is None:
            return []

        return [
            self._format_progress_line("누적 솔 에르다", summary.sol_erda),
            self._format_progress_line("누적 조각", summary.fragments),
        ]

    @staticmethod
    def _format_progress_line(label: str, progress: HexaResourceProgress) -> str:
        return (
            f"• {label} : {progress.current:,} / {progress.maximum:,} "
            f"({progress.percent}%)"
        )
