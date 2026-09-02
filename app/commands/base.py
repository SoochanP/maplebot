from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.command import ParsedCommand


class CommandHandler(ABC):
    command_name: str
    command_aliases: tuple[str, ...] = ()
    requires_character_name: bool = True
    requires_argument_text: bool = False
    usage_example: str | None = None
    missing_argument_message: str = "\uce90\ub9ad\ud130\uba85\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694."

    @property
    def command_names(self) -> tuple[str, ...]:
        return (self.command_name, *self.command_aliases)

    @property
    def resolved_usage_example(self) -> str:
        if self.usage_example is not None:
            return self.usage_example
        if self.requires_character_name:
            return f"!{self.command_name} \uce90\ub9ad\ud130\uba85"
        if self.requires_argument_text:
            return f"!{self.command_name} \uc785\ub825\uac12"
        return f"!{self.command_name}"

    @staticmethod
    def require_character_name(command: ParsedCommand) -> str:
        character_name = command.character_name
        if character_name is None:
            raise ValueError("character_name is required for this command")
        return character_name

    @staticmethod
    def require_argument_text(command: ParsedCommand) -> str:
        argument_text = command.argument_text
        if argument_text is None:
            raise ValueError("argument_text is required for this command")
        return argument_text

    @abstractmethod
    async def handle(self, command: ParsedCommand) -> str:
        raise NotImplementedError
