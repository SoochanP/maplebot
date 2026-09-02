from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.commands.notice import NoticeCommand
from app.models.command import ParsedCommand
from app.models.notice import NoticeFeed, NoticeItem


_KST = timezone(timedelta(hours=9))


class FakeNoticeReader:
    def __init__(self, feed: NoticeFeed) -> None:
        self.feed = feed
        self.received_limits: list[int] = []

    async def fetch_latest_notices(self, *, limit: int = 5) -> NoticeFeed:
        self.received_limits.append(limit)
        return self.feed


def test_notice_command_formats_latest_notices() -> None:
    reader = FakeNoticeReader(
        NoticeFeed(
            items=[
                NoticeItem(title="점검 안내", published_at=datetime(2026, 9, 2, 10, 0, tzinfo=_KST)),
                NoticeItem(title="이벤트 안내", published_at=datetime(2026, 9, 1, 18, 0, tzinfo=_KST)),
            ]
        )
    )
    command = NoticeCommand(reader, notice_limit=5)

    result = asyncio.run(
        command.handle(
            ParsedCommand(
                raw_text="!공지",
                command="공지",
                character_name=None,
            )
        )
    )

    assert reader.received_limits == [5]
    assert result == (
        "[메이플스토리 최신 공지]\n\n"
        "1. 09/02 점검 안내\n"
        "2. 09/01 이벤트 안내"
    )
