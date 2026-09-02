from __future__ import annotations

from collections.abc import Iterable

from app.commands.base import CommandHandler
from app.core.exceptions import InvalidCommandError, UnsupportedCommandError
from app.models.command import ParsedCommand


class CommandRouter:
    def __init__(self, handlers: Iterable[CommandHandler]) -> None:
        self._handlers = {handler.command_name: handler for handler in handlers}
        self._command_names = sorted(
            self._handlers,
            key=lambda command_name: (-len(command_name.split()), -len(command_name)),
        )

    def parse(self, raw_text: str) -> ParsedCommand:
        cleaned = raw_text.strip()
        if not cleaned:
            raise InvalidCommandError("명령어를 입력해주세요.")

        if not cleaned.startswith("!"):
            raise InvalidCommandError("명령어는 !로 시작해야 합니다.")

        if cleaned == "!":
            raise InvalidCommandError("명령어 이름을 입력해주세요.")

        if cleaned[1].isspace():
            raise InvalidCommandError("명령어 형식이 올바르지 않습니다. 예시: !환산 캐릭터명")

        command_body = cleaned[1:]
        matched_command_name = self._find_command_name(command_body)
        if matched_command_name is None:
            raise UnsupportedCommandError("지원하지 않는 명령어입니다.")

        handler = self._handlers[matched_command_name]
        argument_text = command_body[len(matched_command_name):].strip()
        if handler.requires_character_name:
            if not argument_text:
                raise InvalidCommandError("캐릭터명을 입력해주세요.")
            character_name = argument_text
        else:
            if argument_text:
                raise InvalidCommandError(
                    f"명령어 형식이 올바르지 않습니다. 예시: {handler.resolved_usage_example}"
                )
            character_name = None

        return ParsedCommand(
            raw_text=cleaned,
            command=matched_command_name,
            character_name=character_name,
        )

    async def dispatch(self, raw_text: str) -> str:
        parsed_command = self.parse(raw_text)
        handler = self._handlers[parsed_command.command]
        return await handler.handle(parsed_command)

    def peek_command_name(self, raw_text: str) -> str | None:
        cleaned = raw_text.strip()
        if not cleaned.startswith("!"):
            return None

        if cleaned == "!" or cleaned[1].isspace():
            return None

        return self._find_command_name(cleaned[1:])

    def _find_command_name(self, command_body: str) -> str | None:
        for command_name in self._command_names:
            if command_body == command_name:
                return command_name
            if command_body.startswith(f"{command_name} "):
                return command_name
        return None
