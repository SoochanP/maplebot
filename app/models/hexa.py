from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HexaCore(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    level: int
    core_type: str | None = None
    linked_skills: list[str] = Field(default_factory=list)


class HexaStatCore(BaseModel):
    model_config = ConfigDict(frozen=True)

    slot_id: str | None = None
    main_stat_name: str | None = None
    main_stat_level: int | None = None
    sub_stat_name_1: str | None = None
    sub_stat_level_1: int | None = None
    sub_stat_name_2: str | None = None
    sub_stat_level_2: int | None = None
    stat_grade: int | None = None


class HexaStatSet(BaseModel):
    model_config = ConfigDict(frozen=True)

    label: str
    cores: list[HexaStatCore] = Field(default_factory=list)


class HexaOverview(BaseModel):
    model_config = ConfigDict(frozen=True)

    character_name: str
    cores: list[HexaCore] = Field(default_factory=list)
    stat_sets: list[HexaStatSet] = Field(default_factory=list)
