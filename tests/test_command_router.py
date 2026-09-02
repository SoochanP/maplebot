from __future__ import annotations

import asyncio

import pytest

from app.commands.base import CommandHandler
from app.commands.router import CommandRouter
from app.core.exceptions import InvalidCommandError, UnsupportedCommandError
from app.models.command import ParsedCommand


class EchoConvertedStatHandler(CommandHandler):
    command_name = "환산"

    async def handle(self, command: ParsedCommand) -> str:
        return f"{command.command}:{command.character_name}"


class EchoExperienceHistoryHandler(CommandHandler):
    command_name = "경험치 히스토리"

    async def handle(self, command: ParsedCommand) -> str:
        return f"{command.command}:{command.character_name}"


class EchoNoticeHandler(CommandHandler):
    command_name = "공지"
    requires_character_name = False
    usage_example = "!공지"

    async def handle(self, command: ParsedCommand) -> str:
        return command.command


def build_router() -> CommandRouter:
    return CommandRouter(
        handlers=[
            EchoConvertedStatHandler(),
            EchoExperienceHistoryHandler(),
            EchoNoticeHandler(),
        ]
    )


def test_parse_valid_converted_stat_command() -> None:
    router = build_router()

    parsed = router.parse("!환산 SomeCharacter")

    assert parsed.command == "환산"
    assert parsed.character_name == "SomeCharacter"


def test_parse_valid_experience_history_command() -> None:
    router = build_router()

    parsed = router.parse("!경험치 히스토리 창킬")

    assert parsed.command == "경험치 히스토리"
    assert parsed.character_name == "창킬"


def test_parse_valid_notice_command_without_character_name() -> None:
    router = build_router()

    parsed = router.parse("!공지")

    assert parsed.command == "공지"
    assert parsed.character_name is None


def test_parse_missing_character_name() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="캐릭터명을 입력해주세요."):
        router.parse("!환산")


def test_parse_missing_character_name_for_multiword_command() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="캐릭터명을 입력해주세요."):
        router.parse("!경험치 히스토리")


def test_parse_notice_rejects_unexpected_argument() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match=r"예시: !공지"):
        router.parse("!공지 창킬")


def test_parse_unsupported_command() -> None:
    router = build_router()

    with pytest.raises(UnsupportedCommandError, match="지원하지 않는 명령어입니다."):
        router.parse("!없는명령어 캐릭터명")


def test_parse_whitespace_handling() -> None:
    router = build_router()

    parsed = router.parse("   !경험치 히스토리    햇살렌   ")

    assert parsed.command == "경험치 히스토리"
    assert parsed.character_name == "햇살렌"


def test_parse_korean_character_name() -> None:
    router = build_router()

    parsed = router.parse("!환산 김메이플")

    assert parsed.character_name == "김메이플"


def test_parse_missing_bang_prefix() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="명령어는 !로 시작해야 합니다."):
        router.parse("환산 캐릭터명")


def test_parse_bang_only() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="명령어 이름을 입력해주세요."):
        router.parse("!")


def test_parse_space_after_bang_is_invalid() -> None:
    router = build_router()

    with pytest.raises(InvalidCommandError, match="명령어 형식이 올바르지 않습니다."):
        router.parse("! 환산 창킬")


def test_dispatch_uses_registered_handler() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!환산 햇살렌"))

    assert result == "환산:햇살렌"


def test_dispatch_uses_longest_matching_command_name() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!경험치 히스토리 창킬"))

    assert result == "경험치 히스토리:창킬"


def test_dispatch_notice_without_character_name() -> None:
    router = build_router()

    result = asyncio.run(router.dispatch("!공지"))

    assert result == "공지"
