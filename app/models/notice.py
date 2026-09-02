from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoticeItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    url: str | None = None
    published_at: datetime


class NoticeFeed(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[NoticeItem] = Field(default_factory=list)

