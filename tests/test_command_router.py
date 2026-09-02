from __future__ import annotations

import asyncio

import pytest

from app.commands.base import CommandHandler
from app.commands.router import CommandRouter
from app.core.exceptions import InvalidCommandError, UnsupportedCommandError
from app.models.command import ParsedCommand


class EchoConvertedStatHandler(CommandHandler):
    command_name = "\ud658\uc0b0"

    async def handle(self, command: ParsedCommand) -> str:
        return f"{command.command}:{command.character_name}"


class EchoExperienceHistoryHandler(CommandHandler):
    command_name = "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac"
    command_aliases = ("\uacbd\ud5d8\uce58",)

    async def handle(self, command: ParsedCommand) -> str:
        return f"{command.command}:{command.character_name}"


class EchoHexaCostHandler(CommandHandler):
    command_name = "\ud5e5\uc0ac\ube44\uc6a9"
    requires_character_name = False
    requires_argument_text = True
    usage_example = "!\ud5e5\uc0ac\ube44\uc6a9 1->30"
    missing_argument_message = "\ub808\ubca8 \uad6c\uac04\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608\uc2dc: !\ud5e5\uc0ac\ube44\uc6a9 1->30"

    async def handle(self, command: ParsedCommand) -> str:
        return f"{command.command}:{command.argument_text}"


class EchoNoticeHandler(CommandHandler):
    command_name = "\uacf5\uc9c0"
    requires_character_name = False
    usage_example = "!\uacf5\uc9c0"

    async def handle(self, command: ParsedCommand) -> str:
        return command.command



def build_router() -> CommandRouter:
    return CommandRouter(
        handlers=[
            EchoConvertedStatHandler(),
            EchoExperienceHistoryHandler(),
            EchoHexaCostHandler(),
            EchoNoticeHandler(),
        ]
    )


def test_parse_valid_converted_stat_command() -> None:
    router = build_router()

    parsed = router.parse("!\ud658\uc0b0 SomeCharacter")

    assert parsed.command == "\ud658\uc0b0"
    assert parsed.character_name == "SomeCharacter"
    assert parsed.argument_text == "SomeCharacter"


def test_parse_valid_experience_history_command() -> None:
    router = build_router()

    parsed = router.parse("!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac")

    assert parsed.command == "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac"
    assert parsed.character_name == "\ucc3d\ud0ac"
    assert parsed.argument_text == "\ucc3d\ud0ac"


def test_parse_valid_experience_history_alias_command() -> None:
    router = build_router()

    parsed = router.parse("!\uacbd\ud5d8\uce58 \ucc3d\ud0ac")

    assert parsed.command == "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac"
    assert parsed.character_name == "\ucc3d\ud0ac"
    assert parsed.argument_text == "\ucc3d\ud0ac"


def test_parse_valid_hexa_cost_command_with_arrow_format() -> None:
    router = build_router()

    parsed = router.parse("!\ud5e5\uc0ac\ube44\uc6a9 1->30")

    assert parsed.command == "\ud5e5\uc0ac\ube44\uc6a9"
    assert parsed.character_name is None
    assert parsed.argument_text == "1->30"


def test_parse_valid_hexa_cost_command_with_space_format() -> None:
    router = build_router()

    parsed = router.parse("!\ud5e5\uc0ac\ube44\uc6a9 1 30")

    assert parsed.command == "\ud5e5\uc0ac\ube44\uc6a9"
    assert parsed.character_name is None
    assert parsed.argument_text == "1 30"


def test_parse_valid_notice_command_without_character_name() -> None:
    router = build_router()

    parsed = router.parse("!\uacf5\uc9c0")

    assert parsed.command == "\uacf5\uc9c0"
    assert parsed.character_name is None
    assert parsed.argument_text is None


def test_parse_missing_character_name() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="\uce90\ub9ad\ud130\uba85\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694."):
        router.parse("!\ud658\uc0b0")


def test_parse_missing_character_name_for_multiword_command() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="\uce90\ub9ad\ud130\uba85\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694."):
        router.parse("!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac")


def test_parse_missing_argument_for_hexa_cost_command() -> None:
    router = build_router()

    with pytest.raises(
        InvalidCommandError,
        match="\ub808\ubca8 \uad6c\uac04\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694. \uc608\uc2dc: !\ud5e5\uc0ac\ube44\uc6a9 1->30",
    ):
        router.parse("!\ud5e5\uc0ac\ube44\uc6a9")


def test_parse_notice_rejects_unexpected_argument() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match=r"\uc608\uc2dc: !\uacf5\uc9c0"):
        router.parse("!\uacf5\uc9c0 \ucc3d\ud0ac")


def test_parse_unsupported_command() -> None:
    router = build_router()

    with pytest.raises(UnsupportedCommandError, match="\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."):
        router.parse("!\uc5c6\ub294\uba85\ub839\uc5b4 \uce90\ub9ad\ud130\uba85")


def test_parse_whitespace_handling() -> None:
    router = build_router()

    parsed = router.parse("   !\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac    \ud587\uc0b4\ub80c   ")

    assert parsed.command == "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac"
    assert parsed.character_name == "\ud587\uc0b4\ub80c"


def test_parse_korean_character_name() -> None:
    router = build_router()

    parsed = router.parse("!\ud658\uc0b0 \uae40\uba54\uc774\ud50c")

    assert parsed.character_name == "\uae40\uba54\uc774\ud50c"


def test_parse_missing_bang_prefix() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="\uba85\ub839\uc5b4\ub294 !\ub85c \uc2dc\uc791\ud574\uc57c \ud569\ub2c8\ub2e4."):
        router.parse("\ud658\uc0b0 \uce90\ub9ad\ud130\uba85")


def test_parse_bang_only() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="\uba85\ub839\uc5b4 \uc774\ub984\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694."):
        router.parse("!")


def test_parse_space_after_bang_is_invalid() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="\uba85\ub839\uc5b4 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4."):
        router.parse("! \ud658\uc0b0 \ucc3d\ud0ac")


def test_dispatch_uses_registered_handler() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!\ud658\uc0b0 \ud587\uc0b4\ub80c"))

    assert result == "\ud658\uc0b0:\ud587\uc0b4\ub80c"


def test_dispatch_uses_longest_matching_command_name() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"))

    assert result == "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac:\ucc3d\ud0ac"


def test_dispatch_uses_experience_history_alias() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!\uacbd\ud5d8\uce58 \ucc3d\ud0ac"))

    assert result == "\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac:\ucc3d\ud0ac"


def test_dispatch_notice_without_character_name() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!\uacf5\uc9c0"))

    assert result == "\uacf5\uc9c0"


def test_dispatch_hexa_cost_command() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!\ud5e5\uc0ac\ube44\uc6a9 6->21"))

    assert result == "\ud5e5\uc0ac\ube44\uc6a9:6->21"