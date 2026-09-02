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
                raw_text="!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac",
                command="\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac",
                character_name="\ucc3d\ud0ac",
                argument_text="\ucc3d\ud0ac",
            )
        )
    )

    assert crawler.received_names == ["\ucc3d\ud0ac"]
    return result


def test_experience_history_command_selects_latest_five_from_unsorted_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="\ucc3d\ud0ac",
            world_name="\uc2a4\uce74\ub2c8\uc544",
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
        "[\ucc3d\ud0ac] - \uc2a4\uce74\ub2c8\uc544\n\n"
        "01\uc6d4 08\uc77c : Lv.289 31.845%\n"
        "01\uc6d4 09\uc77c : Lv.289 33.576% (+2.5\uc870)\n"
        "01\uc6d4 10\uc77c : Lv.289 35.527% (+2.8\uc870)\n"
        "01\uc6d4 11\uc77c : Lv.289 40.050% (+6.6\uc870)\n"
        "01\uc6d4 12\uc77c : Lv.289 41.334% (+1.9\uc870)\n\n"
        "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 3.5\uc870\n"
        "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 85.5\uc870\n"
        "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
        "25\ub144 02\uc6d4 06\uc77c (25\uc77c \ud6c4)"
    )


def test_experience_history_command_formats_exactly_five_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="\ucc3d\ud0ac",
            world_name="\uc624\ub85c\ub77c",
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
        "[\ucc3d\ud0ac] - \uc624\ub85c\ub77c\n\n"
        "02\uc6d4 01\uc77c : Lv.280 1.000%\n"
        "02\uc6d4 02\uc77c : Lv.280 2.000% (+100 EXP)\n"
        "02\uc6d4 03\uc77c : Lv.280 3.000% (+100 EXP)\n"
        "02\uc6d4 04\uc77c : Lv.280 4.000% (+100 EXP)\n"
        "02\uc6d4 05\uc77c : Lv.280 5.000% (+100 EXP)\n\n"
        "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 100 EXP\n"
        "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 9,500 EXP\n"
        "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
        "25\ub144 05\uc6d4 11\uc77c (95\uc77c \ud6c4)"
    )


def test_experience_history_command_formats_fewer_than_five_entries() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="\ucc3d\ud0ac",
            world_name="\ubca0\ub77c",
            entries=[
                build_entry(2025, 3, 1, level=281, experience=1000, experience_percent="10.000"),
                build_entry(2025, 3, 2, level=281, experience=1250, experience_percent="12.500"),
                build_entry(2025, 3, 3, level=281, experience=1500, experience_percent="15.000"),
            ],
        )
    )

    assert result == (
        "[\ucc3d\ud0ac] - \ubca0\ub77c\n\n"
        "03\uc6d4 01\uc77c : Lv.281 10.000%\n"
        "03\uc6d4 02\uc77c : Lv.281 12.500% (+250 EXP)\n"
        "03\uc6d4 03\uc77c : Lv.281 15.000% (+250 EXP)\n\n"
        "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 250 EXP\n"
        "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 8,500 EXP\n"
        "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
        "25\ub144 04\uc6d4 06\uc77c (34\uc77c \ud6c4)"
    )


def test_experience_history_command_calculates_level_up_gain_and_uses_snapshot_time_for_same_day_records() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="\ucc3d\ud0ac",
            world_name="\ub8e8\ub098",
            entries=[
                build_entry(2025, 8, 31, level=290, experience=1550, experience_percent="15.500"),
                build_entry(2025, 8, 30, level=290, experience=1200, experience_percent="12.000", hour=23),
                build_entry(2025, 8, 29, level=289, experience=9800, experience_percent="98.500"),
                build_entry(2025, 8, 30, level=290, experience=1023, experience_percent="10.231", hour=1),
            ],
        )
    )

    assert result == (
        "[\ucc3d\ud0ac] - \ub8e8\ub098\n\n"
        "08\uc6d4 29\uc77c : Lv.289 98.500%\n"
        "08\uc6d4 30\uc77c : Lv.290 10.231% (+1,172 EXP)\n"
        "08\uc6d4 30\uc77c : Lv.290 12.000% (+177 EXP)\n"
        "08\uc6d4 31\uc77c : Lv.290 15.500% (+350 EXP)\n\n"
        "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 566 EXP\n"
        "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 8,450 EXP\n"
        "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
        "25\ub144 09\uc6d4 15\uc77c (15\uc77c \ud6c4)"
    )


def test_experience_history_command_formats_zero_gain_and_unavailable_prediction() -> None:
    result = dispatch(
        ExperienceHistory(
            character_name="\ucc3d\ud0ac",
            world_name="\uc5d8\ub9ac\uc2dc\uc6c0",
            entries=[
                build_entry(2025, 9, 1, level=282, experience=250, experience_percent="25.000"),
                build_entry(2025, 9, 2, level=282, experience=250, experience_percent="25.000"),
            ],
        )
    )

    assert result == (
        "[\ucc3d\ud0ac] - \uc5d8\ub9ac\uc2dc\uc6c0\n\n"
        "09\uc6d4 01\uc77c : Lv.282 25.000%\n"
        "09\uc6d4 02\uc77c : Lv.282 25.000% (+0)\n\n"
        "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 0\n"
        "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 750 EXP\n"
        "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
        "\uacc4\uc0b0 \ubd88\uac00"
    )