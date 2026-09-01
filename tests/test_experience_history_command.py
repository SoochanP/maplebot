from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

from app.commands.experience_history import ExperienceHistoryCommand
from app.models.command import ParsedCommand
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry


class FakeCrawler:
    def __init__(self, history: ExperienceHistory) -> None:
        self.history = history
        self.received_names: list[str] = []

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        self.received_names.append(character_name)
        return self.history


def build_entry(
    year: int,
    month: int,
    day: int,
    *,
    level: int,
    experience: int,
    experience_percent: str,
    hour: int = 0,
    minute: int = 0,
) -> ExperienceHistoryEntry:
    snapshot_at = datetime(year, month, day, hour, minute, tzinfo=timezone.utc)
    return ExperienceHistoryEntry(
        date=date(year, month, day),
        snapshot_at=snapshot_at,
        level=level,
        experience=experience,
        experience_percent=Decimal(experience_percent),
    )


def dispatch(history: ExperienceHistory) -> str:
    crawler = FakeCrawler(history)
    command = ExperienceHistoryCommand(crawler)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!경험치 히스토리 창킬",
                command="경험치 히스토리",
                character_name="창킬",
            )
        )
    )

    assert crawler.received_names == ["창킬"]
    return result


def test_experience_history_command_selects_latest_five_from_unsorted_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="창킬",
            entries=[
                build_entry(2025, 1, 10, level=289, experience=51761074759717, experience_percent="35.527"),
                build_entry(2025, 1, 6, level=289, experience=37154536048390, experience_percent="25.501"),
                build_entry(2025, 1, 12, level=289, experience=60221558626871, experience_percent="41.334"),
                build_entry(2025, 1, 8, level=289, experience=46396709843484, experience_percent="31.845"),
                build_entry(2025, 1, 11, level=289, experience=58351154293278, experience_percent="40.050"),
                build_entry(2025, 1, 7, level=289, experience=39261249135325, experience_percent="26.947"),
                build_entry(2025, 1, 9, level=289, experience=48919197471076, experience_percent="33.576"),
            ],
        )
    )

    assert result == (
        "[창킬 경험치 히스토리]\n\n"
        "01/08  Lv.289  31.845%\n"
        "01/09  Lv.289  33.576%  (+1.731%)\n"
        "01/10  Lv.289  35.527%  (+1.951%)\n"
        "01/11  Lv.289  40.050%  (+4.523%)\n"
        "01/12  Lv.289  41.334%  (+1.284%)\n\n"
        "최근 5개 기록 변화: +13,824,848,783,387 EXP (+9.489%)"
    )


def test_experience_history_command_formats_exactly_five_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="창킬",
            entries=[
                build_entry(2025, 2, 1, level=280, experience=100, experience_percent="1.000"),
                build_entry(2025, 2, 2, level=280, experience=200, experience_percent="2.000"),
                build_entry(2025, 2, 3, level=280, experience=300, experience_percent="3.000"),
                build_entry(2025, 2, 4, level=280, experience=400, experience_percent="4.000"),
                build_entry(2025, 2, 5, level=280, experience=500, experience_percent="5.000"),
            ],
        )
    )

    assert result == (
        "[창킬 경험치 히스토리]\n\n"
        "02/01  Lv.280  1.000%\n"
        "02/02  Lv.280  2.000%  (+1.000%)\n"
        "02/03  Lv.280  3.000%  (+1.000%)\n"
        "02/04  Lv.280  4.000%  (+1.000%)\n"
        "02/05  Lv.280  5.000%  (+1.000%)\n\n"
        "최근 5개 기록 변화: +400 EXP (+4.000%)"
    )


def test_experience_history_command_formats_fewer_than_five_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="창킬",
            entries=[
                build_entry(2025, 3, 1, level=281, experience=1000, experience_percent="10.000"),
                build_entry(2025, 3, 2, level=281, experience=1250, experience_percent="12.500"),
                build_entry(2025, 3, 3, level=281, experience=1500, experience_percent="15.000"),
            ],
        )
    )

    assert result == (
        "[창킬 경험치 히스토리]\n\n"
        "03/01  Lv.281  10.000%\n"
        "03/02  Lv.281  12.500%  (+2.500%)\n"
        "03/03  Lv.281  15.000%  (+2.500%)\n\n"
        "최근 3개 기록 변화: +500 EXP (+5.000%)"
    )


def test_experience_history_command_marks_level_up_and_uses_snapshot_time_for_same_day_records() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="창킬",
            entries=[
                build_entry(2025, 8, 31, level=290, experience=1550, experience_percent="15.500"),
                build_entry(2025, 8, 30, level=290, experience=1200, experience_percent="12.000", hour=23),
                build_entry(2025, 8, 29, level=289, experience=9850, experience_percent="98.500"),
                build_entry(2025, 8, 30, level=290, experience=1023, experience_percent="10.231", hour=1),
            ],
        )
    )

    assert result == (
        "[창킬 경험치 히스토리]\n\n"
        "08/29  Lv.289  98.500%\n"
        "08/30  Lv.290  10.231%  (레벨업)\n"
        "08/30  Lv.290  12.000%  (+1.769%)\n"
        "08/31  Lv.290  15.500%  (+3.500%)"
    )
