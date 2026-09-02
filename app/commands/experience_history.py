from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Protocol

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry


class ExperienceHistoryReader(Protocol):
    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        ...


class ExperienceHistoryCommand(CommandHandler):
    command_name = "경험치"

    def __init__(
        self,
        crawler: ExperienceHistoryReader,
        *,
        recent_entry_count: int = 5,
    ) -> None:
        self._crawler = crawler
        self._recent_entry_count = recent_entry_count

    async def handle(self, command: ParsedCommand) -> str:
        character_name = self.require_character_name(command)
        history = await self._crawler.fetch_experience_history(character_name)
        return self._format_response(history)

    def _format_response(self, history: ExperienceHistory) -> str:
        recent_entries = self._select_recent_entries(history.entries)
        lines = [f"[{history.character_name} 경험치 히스토리]", ""]
        previous_entry: ExperienceHistoryEntry | None = None

        for entry in recent_entries:
            lines.append(self._format_entry_line(entry, previous_entry))
            previous_entry = entry

        summary_line = self._build_summary_line(recent_entries)
        if summary_line is not None:
            lines.extend(["", summary_line])

        return "\n".join(lines)

    def _select_recent_entries(
        self,
        entries: list[ExperienceHistoryEntry],
    ) -> list[ExperienceHistoryEntry]:
        sorted_entries = sorted(entries, key=self._entry_sort_key)
        return sorted_entries[-self._recent_entry_count :]

    def _format_entry_line(
        self,
        entry: ExperienceHistoryEntry,
        previous_entry: ExperienceHistoryEntry | None,
    ) -> str:
        line = f"{entry.date:%m/%d}  Lv.{entry.level}  {entry.experience_percent:.3f}%"
        delta_suffix = self._build_delta_suffix(entry, previous_entry)
        if delta_suffix is not None:
            line = f"{line}  {delta_suffix}"
        return line

    def _build_delta_suffix(
        self,
        entry: ExperienceHistoryEntry,
        previous_entry: ExperienceHistoryEntry | None,
    ) -> str | None:
        if previous_entry is None:
            return None

        if entry.level == previous_entry.level:
            percent_change = entry.experience_percent - previous_entry.experience_percent
            return f"({percent_change:+.3f}%)"

        if entry.level > previous_entry.level:
            return "(레벨업)"

        return None

    def _build_summary_line(self, entries: list[ExperienceHistoryEntry]) -> str | None:
        if len(entries) < 2 or not self._supports_exact_window_gain(entries):
            return None

        total_experience_gain = entries[-1].experience - entries[0].experience
        total_percent_gain = entries[-1].experience_percent - entries[0].experience_percent
        return (
            f"최근 {len(entries)}개 기록 변화: "
            f"{total_experience_gain:+,} EXP ({total_percent_gain:+.3f}%)"
        )

    @staticmethod
    def _supports_exact_window_gain(entries: list[ExperienceHistoryEntry]) -> bool:
        base_level = entries[0].level
        return all(entry.level == base_level for entry in entries)

    @staticmethod
    def _entry_sort_key(entry: ExperienceHistoryEntry) -> tuple[datetime, int, int]:
        return (
            ExperienceHistoryCommand._normalized_snapshot_at(entry),
            entry.level,
            entry.experience,
        )

    @staticmethod
    def _normalized_snapshot_at(entry: ExperienceHistoryEntry) -> datetime:
        if entry.snapshot_at is None:
            return datetime.combine(entry.date, time.min, tzinfo=timezone.utc)

        if entry.snapshot_at.tzinfo is None:
            return entry.snapshot_at.replace(tzinfo=timezone.utc)

        return entry.snapshot_at.astimezone(timezone.utc)
