from __future__ import annotations

from collections.abc import Iterable

from app.commands.base import CommandHandler
from app.core.exceptions import InvalidCommandError, UnsupportedCommandError
from app.models.command import ParsedCommand


class CommandRouter:
    def __init__(self, handlers: Iterable[CommandHandler]) -> None:
        self._handlers_by_name: dict[str, CommandHandler] = {}
        for handler in handlers:
            for command_name in handler.command_names:
                if command_name in self._handlers_by_name:
                    raise ValueError(f"duplicate command name: {command_name}")
                self._handlers_by_name[command_name] = handler

        self._command_names = sorted(
            self._handlers_by_name,
            key=lambda command_name: (-len(command_name.split()), -len(command_name)),
        )

    def parse(self, raw_text: str) -> ParsedCommand:
        cleaned = raw_text.strip()
        if not cleaned:
            raise InvalidCommandError("\uba85\ub839\uc5b4\ub97c \uc785\ub825\ud574\uc8fc\uc138\uc694.")

        if not cleaned.startswith("!"):
            raise InvalidCommandError("\uba85\ub839\uc5b4\ub294 !\ub85c \uc2dc\uc791\ud574\uc57c \ud569\ub2c8\ub2e4.")

        if cleaned == "!":
            raise InvalidCommandError("\uba85\ub839\uc5b4 \uc774\ub984\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694.")

        if cleaned[1].isspace():
            raise InvalidCommandError(
                "\uba85\ub839\uc5b4 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc608\uc2dc: !\ud658\uc0b0 \uce90\ub9ad\ud130\uba85"
            )

        command_body = cleaned[1:]
        matched_command_name = self._find_command_name(command_body)
        if matched_command_name is None:
            raise UnsupportedCommandError("\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4.")

        handler = self._handlers_by_name[matched_command_name]
        argument_text = command_body[len(matched_command_name) :].strip()
        character_name: str | None = None

        if handler.requires_character_name:
            if not argument_text:
                raise InvalidCommandError(handler.missing_argument_message)
            character_name = argument_text
        elif handler.requires_argument_text:
            if not argument_text:
                raise InvalidCommandError(handler.missing_argument_message)
        elif argument_text:
            raise InvalidCommandError(
                f"\uba85\ub839\uc5b4 \ud615\uc2dd\uc774 \uc62c\ubc14\ub974\uc9c0 \uc54a\uc2b5\ub2c8\ub2e4. \uc608\uc2dc: {handler.resolved_usage_example}"
            )

        return ParsedCommand(
            raw_text=cleaned,
            command=handler.command_name,
            character_name=character_name,
            argument_text=argument_text or None,
        )

    async def dispatch(self, raw_text: str) -> str:
        parsed_command = self.parse(raw_text)
        handler = self._handlers_by_name[parsed_command.command]
        return await handler.handle(parsed_command)

    def peek_command_name(self, raw_text: str) -> str | None:
        cleaned = raw_text.strip()
        if not cleaned.startswith("!"):
            return None

        if cleaned == "!" or cleaned[1].isspace():
            return None

        matched_command_name = self._find_command_name(cleaned[1:])
        if matched_command_name is None:
            return None

        return self._handlers_by_name[matched_command_name].command_name

    def _find_command_name(self, command_body: str) -> str | None:
        for command_name in self._command_names:
            if command_body == command_name:
                return command_name
            if command_body.startswith(f"{command_name} "):
                return command_name
        return None
