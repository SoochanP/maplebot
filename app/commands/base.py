from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.command import ParsedCommand


class CommandHandler(ABC):
    command_name: str
    requires_character_name: bool = True
    usage_example: str | None = None

    @property
    def resolved_usage_example(self) -> str:
        if self.usage_example is not None:
            return self.usage_example
        if self.requires_character_name:
            return f"!{self.command_name} 캐릭터명"
        return f"!{self.command_name}"

    @staticmethod
    def require_character_name(command: ParsedCommand) -> str:
        character_name = command.character_name
        if character_name is None:
            raise ValueError("character_name is required for this command")
        return character_name

    @abstractmethod
    async def handle(self, command: ParsedCommand) -> str:
        raise NotImplementedError
