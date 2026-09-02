from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Protocol

from app.commands.base import CommandHandler
from app.data.experience_table import get_kms_next_level_experience
from app.models.command import ParsedCommand
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry


_ONE_DECIMAL_PLACE = Decimal("0.1")
_THREE_DECIMAL_PLACES = Decimal("0.001")
_ONE_TRILLION = Decimal("1000000000000")
_ONE_HUNDRED = Decimal("100")


class ExperienceHistoryReader(Protocol):
    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        ...


class ExperienceHistoryCommand(CommandHandler):
    command_name = "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac"
    command_aliases = ("\uacbd\ud5d8\uce58",)

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
        if not recent_entries:
            return self._format_header(history)

        lines = [self._format_header(history), ""]
        gains: list[int | None] = []
        previous_entry: ExperienceHistoryEntry | None = None

        for entry in recent_entries:
            gain = None if previous_entry is None else self._calculate_experience_gain(previous_entry, entry)
            if previous_entry is not None:
                gains.append(gain)
            lines.append(self._format_entry_line(entry, gain))
            previous_entry = entry

        lines.extend(["", *self._build_summary_lines(recent_entries, gains)])
        return "\n".join(lines)

    def _select_recent_entries(
        self,
        entries: list[ExperienceHistoryEntry],
    ) -> list[ExperienceHistoryEntry]:
        sorted_entries = sorted(entries, key=self._entry_sort_key)
        return sorted_entries[-self._recent_entry_count :]

    def _format_header(self, history: ExperienceHistory) -> str:
        if history.world_name:
            return f"[{history.character_name}] - {history.world_name}"
        return f"[{history.character_name}]"

    def _format_entry_line(self, entry: ExperienceHistoryEntry, gain: int | None) -> str:
        line = f"{entry.date:%m\uc6d4 %d\uc77c} : Lv.{entry.level} {entry.experience_percent:.3f}%"
        if gain is not None:
            line = f"{line} ({self._format_signed_experience(gain)})"
        return line

    def _build_summary_lines(
        self,
        entries: list[ExperienceHistoryEntry],
        gains: list[int | None],
    ) -> list[str]:
        average_text = "\uacc4\uc0b0 \ubd88\uac00"
        prediction_text = "\uacc4\uc0b0 \ubd88\uac00"
        remaining_experience = self._calculate_remaining_experience(entries[-1])
        remaining_text = (
            "\uacc4\uc0b0 \ubd88\uac00"
            if remaining_experience is None
            else self._format_experience_amount(remaining_experience)
        )

        comparable_gains = [gain for gain in gains if gain is not None]
        if gains and len(comparable_gains) == len(gains):
            total_gain = sum(comparable_gains)
            average_gain = Decimal(total_gain) / Decimal(len(comparable_gains))
            average_text = self._format_experience_amount(average_gain)
            prediction_text = self._build_prediction_text(
                latest_date=entries[-1].date,
                remaining_experience=remaining_experience,
                transition_count=len(comparable_gains),
                total_gain=total_gain,
            )

        return [
            f"\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: {average_text}",
            f"\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: {remaining_text}",
            "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:",
            prediction_text,
        ]

    def _build_prediction_text(
        self,
        *,
        latest_date: date,
        remaining_experience: int | None,
        transition_count: int,
        total_gain: int,
    ) -> str:
        if remaining_experience is None or transition_count <= 0 or total_gain <= 0:
            return "\uacc4\uc0b0 \ubd88\uac00"

        days_until_level_up = 0
        if remaining_experience > 0:
            days_until_level_up = (
                (remaining_experience * transition_count) + total_gain - 1
            ) // total_gain

        predicted_date = latest_date + timedelta(days=days_until_level_up)
        return f"{predicted_date:%y\ub144 %m\uc6d4 %d\uc77c} ({days_until_level_up}\uc77c \ud6c4)"

    def _calculate_experience_gain(
        self,
        previous_entry: ExperienceHistoryEntry,
        entry: ExperienceHistoryEntry,
    ) -> int | None:
        if entry.level < previous_entry.level:
            return None

        if entry.level == previous_entry.level:
            return entry.experience - previous_entry.experience

        previous_level_total = self._resolve_next_level_experience(previous_entry)
        if previous_level_total is None:
            return None

        total_gain = previous_level_total - previous_entry.experience
        for level in range(previous_entry.level + 1, entry.level):
            level_total = get_kms_next_level_experience(level)
            if level_total is None:
                return None
            total_gain += level_total

        total_gain += entry.experience
        return total_gain

    def _calculate_remaining_experience(self, entry: ExperienceHistoryEntry) -> int | None:
        next_level_experience = self._resolve_next_level_experience(entry)
        if next_level_experience is None:
            return None

        return max(next_level_experience - entry.experience, 0)

    def _resolve_next_level_experience(self, entry: ExperienceHistoryEntry) -> int | None:
        known_total = get_kms_next_level_experience(entry.level)
        if known_total is not None and self._matches_known_total(entry, known_total):
            return known_total

        if entry.experience_percent == 0:
            return known_total

        inferred_total = (
            Decimal(entry.experience) * _ONE_HUNDRED / entry.experience_percent
        ).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return int(inferred_total)

    @staticmethod
    def _matches_known_total(entry: ExperienceHistoryEntry, known_total: int) -> bool:
        if entry.experience_percent == 0:
            return entry.experience == 0

        known_percent = (
            Decimal(entry.experience) * _ONE_HUNDRED / Decimal(known_total)
        ).quantize(_THREE_DECIMAL_PLACES, rounding=ROUND_HALF_UP)
        entry_percent = entry.experience_percent.quantize(
            _THREE_DECIMAL_PLACES,
            rounding=ROUND_HALF_UP,
        )
        return known_percent == entry_percent

    @staticmethod
    def _format_signed_experience(value: int) -> str:
        sign = "+" if value >= 0 else "-"
        return f"{sign}{ExperienceHistoryCommand._format_experience_amount(abs(value))}"

    @staticmethod
    def _format_experience_amount(value: int | Decimal) -> str:
        decimal_value = Decimal(value)
        if decimal_value == 0:
            return "0"

        if abs(decimal_value) >= _ONE_TRILLION:
            trillion_value = (decimal_value / _ONE_TRILLION).quantize(
                _ONE_DECIMAL_PLACE,
                rounding=ROUND_HALF_UP,
            )
            text = format(trillion_value.normalize(), "f")
            return f"{text}\uc870"

        rounded_value = decimal_value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        return f"{int(rounded_value):,} EXP"

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
