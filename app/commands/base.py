from __future__ import annotations

from abc import ABC, abstractmethod

from app.models.command import ParsedCommand


class CommandHandler(ABC):
    command_name: str

    @abstractmethod
    async def handle(self, command: ParsedCommand) -> str:
        raise NotImplementedError

