from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ExperienceHistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    date: date
    snapshot_at: datetime | None = None
    level: int
    experience: int
    experience_percent: Decimal


class ExperienceHistory(BaseModel):
    model_config = ConfigDict(frozen=True)

    character_name: str
    world_name: str | None = None
    entries: list[ExperienceHistoryEntry]