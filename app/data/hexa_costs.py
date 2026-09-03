from __future__ import annotations

import logging
from collections.abc import Sequence

from app.data.hexa_cost_tables import (
    HEXA_COST_TABLES,
    PROFILE_CLASS_COMMON,
    PROFILE_COMMON,
    PROFILE_ENHANCEMENT,
    PROFILE_EXISTING_SKILL,
    PROFILE_MASTERY,
    PROFILE_ORDER,
    PROFILE_THIRD_SKILL,
)
from app.data.hexa_special_profiles import (
    CLASS_COMMON_CORE_NAMES,
    THIRD_SKILL_CORE_NAMES,
)
from app.models.hexa import HexaCore
from app.models.hexa_cost import (
    HexaCostProfileSummary,
    HexaCostSummary,
    HexaCumulativeCostSummary,
    HexaResourceProgress,
)


logger = logging.getLogger("maplebot.hexa_costs")


def calculate_hexa_cost_summary(current_level: int, target_level: int) -> HexaCostSummary:
    _validate_transition_levels(current_level, target_level)

    return HexaCostSummary(
        current_level=current_level,
        target_level=target_level,
        profiles=[
            calculate_hexa_profile_cost(profile_name, current_level, target_level)
            for profile_name in PROFILE_ORDER
        ],
    )


def calculate_hexa_profile_cost(
    profile_name: str,
    current_level: int,
    target_level: int,
) -> HexaCostProfileSummary:
    _validate_profile_levels(current_level, target_level)
    cost_table = _get_cost_table(profile_name)
    return HexaCostProfileSummary(
        profile_name=profile_name,
        sol_erda=sum(cost[0] for cost in cost_table[current_level:target_level]),
        fragments=sum(cost[1] for cost in cost_table[current_level:target_level]),
    )


def calculate_hexa_cumulative_cost(cores: Sequence[HexaCore]) -> HexaCumulativeCostSummary:
    if not cores:
        return HexaCumulativeCostSummary()

    current_sol_erda = 0
    max_sol_erda = 0
    current_fragments = 0
    max_fragments = 0
    unresolved_core_names: list[str] = []

    for core in cores:
        profile_name = resolve_hexa_cost_profile(core.name, core.core_type)
        if profile_name is None:
            _append_unresolved_core(unresolved_core_names, core.name)
            continue

        try:
            current_cost = calculate_hexa_profile_cost(profile_name, 0, core.level)
            max_cost = calculate_hexa_profile_cost(profile_name, 0, 30)
        except ValueError:
            _append_unresolved_core(unresolved_core_names, core.name)
            continue

        current_sol_erda += current_cost.sol_erda
        max_sol_erda += max_cost.sol_erda
        current_fragments += current_cost.fragments
        max_fragments += max_cost.fragments

    if unresolved_core_names:
        logger.warning("hexa_cost unresolved_cores=%s", ", ".join(unresolved_core_names))
        return HexaCumulativeCostSummary(unresolved_core_names=unresolved_core_names)

    return HexaCumulativeCostSummary(
        sol_erda=HexaResourceProgress(
            current=current_sol_erda,
            maximum=max_sol_erda,
            percent=_calculate_progress_percent(current_sol_erda, max_sol_erda),
        ),
        fragments=HexaResourceProgress(
            current=current_fragments,
            maximum=max_fragments,
            percent=_calculate_progress_percent(current_fragments, max_fragments),
        ),
    )


def resolve_hexa_cost_profile(core_name: str, core_type: str | None) -> str | None:
    normalized_name = core_name.strip()
    normalized_type = None if core_type is None else core_type.strip()

    if not normalized_name or not normalized_type:
        return None

    if normalized_type == "마스터리 코어":
        return PROFILE_MASTERY
    if normalized_type == "강화 코어":
        return PROFILE_ENHANCEMENT
    if normalized_type == "스킬 코어":
        if normalized_name in THIRD_SKILL_CORE_NAMES:
            return PROFILE_THIRD_SKILL
        return PROFILE_EXISTING_SKILL
    if normalized_type == "공용 코어":
        if normalized_name in CLASS_COMMON_CORE_NAMES:
            return PROFILE_CLASS_COMMON
        return PROFILE_COMMON

    return None


def _append_unresolved_core(unresolved_core_names: list[str], core_name: str) -> None:
    if core_name not in unresolved_core_names:
        unresolved_core_names.append(core_name)


def _get_cost_table(profile_name: str) -> tuple[tuple[int, int], ...]:
    try:
        return HEXA_COST_TABLES[profile_name]
    except KeyError as exc:
        raise ValueError(f"unknown HEXA cost profile: {profile_name}") from exc


def _calculate_progress_percent(current: int, maximum: int) -> int:
    if maximum <= 0:
        return 0
    if current >= maximum:
        return 100
    return min((current * 100) // maximum, 99)


def _validate_transition_levels(current_level: int, target_level: int) -> None:
    if current_level < 0 or target_level > 30 or current_level >= target_level:
        raise ValueError("level range must satisfy 0 <= current_level < target_level <= 30")


def _validate_profile_levels(current_level: int, target_level: int) -> None:
    if current_level < 0 or target_level > 30 or current_level > target_level:
        raise ValueError("level range must satisfy 0 <= current_level <= target_level <= 30")
