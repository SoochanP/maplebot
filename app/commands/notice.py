from __future__ import annotations

from typing import Protocol

from app.commands.base import CommandHandler
from app.models.command import ParsedCommand
from app.models.notice import NoticeFeed


class NoticeReader(Protocol):
    async def fetch_latest_notices(self, *, limit: int = 5) -> NoticeFeed:
        ...


class NoticeCommand(CommandHandler):
    command_name = "공지"
    requires_character_name = False
    usage_example = "!공지"

    def __init__(self, reader: NoticeReader, *, notice_limit: int = 5) -> None:
        self._reader = reader
        self._notice_limit = notice_limit

    async def handle(self, command: ParsedCommand) -> str:
        del command
        feed = await self._reader.fetch_latest_notices(limit=self._notice_limit)
        return self._format_response(feed)

    @staticmethod
    def _format_response(feed: NoticeFeed) -> str:
        lines = ["[메이플스토리 최신 공지]", ""]
        for index, item in enumerate(feed.items, start=1):
            lines.append(f"{index}. {item.published_at:%m/%d} {item.title}")
        return "\n".join(lines)
