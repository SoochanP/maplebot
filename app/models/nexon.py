from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class NexonPayloadModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class NexonCharacterIdentifierPayload(NexonPayloadModel):
    ocid: str


class NexonCharacterBasicPayload(NexonPayloadModel):
    date: datetime
    character_name: str
    world_name: str | None = None
    character_class: str | None = None
    character_level: int
    character_exp: int
    character_exp_rate: Decimal


class NexonHexaLinkedSkillPayload(NexonPayloadModel):
    hexa_skill_id: str


class NexonHexaCorePayload(NexonPayloadModel):
    hexa_core_name: str
    hexa_core_level: int
    hexa_core_event_level: int | None = None
    hexa_core_type: str | None = None
    linked_skill: list[NexonHexaLinkedSkillPayload] = Field(default_factory=list)


class NexonCharacterHexaPayload(NexonPayloadModel):
    date: datetime | None = None
    character_hexa_core_equipment: list[NexonHexaCorePayload] = Field(default_factory=list)


class NexonHexaStatCorePayload(NexonPayloadModel):
    slot_id: str | None = None
    main_stat_name: str | None = None
    sub_stat_name_1: str | None = None
    sub_stat_name_2: str | None = None
    main_stat_level: int | None = None
    sub_stat_level_1: int | None = None
    sub_stat_level_2: int | None = None
    stat_grade: int | None = None


class NexonCharacterHexaStatPayload(NexonPayloadModel):
    date: datetime | None = None
    character_class: str | None = None
    character_hexa_stat_core: list[NexonHexaStatCorePayload] = Field(default_factory=list)
    character_hexa_stat_core_2: list[NexonHexaStatCorePayload] = Field(default_factory=list)
    character_hexa_stat_core_3: list[NexonHexaStatCorePayload] = Field(default_factory=list)
    preset_hexa_stat_core: list[NexonHexaStatCorePayload] = Field(default_factory=list)
    preset_hexa_stat_core_2: list[NexonHexaStatCorePayload] = Field(default_factory=list)
    preset_hexa_stat_core_3: list[NexonHexaStatCorePayload] = Field(default_factory=list)


class NexonUnionPayload(NexonPayloadModel):
    date: datetime | None = None
    union_level: int
    union_grade: str | None = None
    union_artifact_level: int | None = None
    union_artifact_exp: int | None = None
    union_artifact_point: int | None = None


class NexonUnionArtifactEffectPayload(NexonPayloadModel):
    name: str
    level: int | None = None


class NexonUnionArtifactPayload(NexonPayloadModel):
    date: datetime | None = None
    union_artifact_effect: list[NexonUnionArtifactEffectPayload] = Field(default_factory=list)
    union_artifact_remain_ap: int | None = None


class NexonUnionChampionBadgePayload(NexonPayloadModel):
    stat: str


class NexonUnionChampionMemberPayload(NexonPayloadModel):
    champion_name: str
    champion_slot: int | None = None
    champion_grade: str | None = None
    champion_class: str | None = None
    champion_badge_info: list[NexonUnionChampionBadgePayload] = Field(default_factory=list)


class NexonUnionChampionPayload(NexonPayloadModel):
    date: datetime | None = None
    union_champion: list[NexonUnionChampionMemberPayload] = Field(default_factory=list)
    champion_badge_total_info: list[NexonUnionChampionBadgePayload] = Field(default_factory=list)


class NexonOverallRankingEntryPayload(NexonPayloadModel):
    date: date
    ranking: int
    character_name: str
    world_name: str
    class_name: str
    sub_class_name: str | None = None
    character_level: int
    character_exp: int | None = None
    character_popularity: int | None = None
    character_guildname: str | None = None


class NexonOverallRankingPayload(NexonPayloadModel):
    ranking: list[NexonOverallRankingEntryPayload] = Field(default_factory=list)


class NexonNoticeItemPayload(NexonPayloadModel):
    title: str
    url: str | None = None
    notice_id: int | None = None
    date: datetime


class NexonNoticePayload(NexonPayloadModel):
    notice: list[NexonNoticeItemPayload] = Field(default_factory=list)
