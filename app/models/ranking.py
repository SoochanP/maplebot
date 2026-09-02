from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class CharacterRanking(BaseModel):
    model_config = ConfigDict(frozen=True)

    character_name: str
    ranking: int
    ranking_date: date
    world_name: str | None = None
    class_name: str | None = None
    sub_class_name: str | None = None
    character_level: int | None = None

