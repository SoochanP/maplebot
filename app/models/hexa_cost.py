from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class HexaCostProfileSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    profile_name: str
    sol_erda: int
    fragments: int

    @property
    def energy(self) -> int:
        return self.sol_erda * 1_000


class HexaCostSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    current_level: int
    target_level: int
    profiles: list[HexaCostProfileSummary] = Field(default_factory=list)
