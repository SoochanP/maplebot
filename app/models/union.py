from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class UnionArtifactEffect(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    level: int | None = None


class UnionChampion(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    class_name: str | None = None
    grade: str | None = None
    badge_effects: list[str] = Field(default_factory=list)


class UnionOverview(BaseModel):
    model_config = ConfigDict(frozen=True)

    character_name: str
    union_level: int
    union_grade: str | None = None
    union_artifact_level: int | None = None
    union_artifact_exp: int | None = None
    union_artifact_point: int | None = None
    union_artifact_remain_ap: int | None = None
    artifact_effects: list[UnionArtifactEffect] = Field(default_factory=list)
    champions: list[UnionChampion] = Field(default_factory=list)
    champion_badge_totals: list[str] = Field(default_factory=list)

