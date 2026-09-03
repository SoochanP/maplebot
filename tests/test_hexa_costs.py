from __future__ import annotations

from app.data.hexa_costs import (
    calculate_hexa_cost_summary,
    calculate_hexa_cumulative_cost,
    resolve_hexa_cost_profile,
)
from app.models.hexa import HexaCore, HexaStatCore, HexaStatSet


def profile_totals(current_level: int, target_level: int) -> dict[str, tuple[int, int]]:
    summary = calculate_hexa_cost_summary(current_level, target_level)
    return {
        profile.profile_name: (profile.sol_erda, profile.fragments)
        for profile in summary.profiles
    }


def build_core(name: str, level: int, core_type: str) -> HexaCore:
    return HexaCore(name=name, level=level, core_type=core_type)


def build_stat_set(label: str) -> HexaStatSet:
    return HexaStatSet(
        label=label,
        cores=[HexaStatCore(main_stat_name="공격력 증가", main_stat_level=1)],
    )


def test_calculate_hexa_cost_summary_matches_golden_values_for_1_to_30() -> None:
    assert profile_totals(1, 30) == {
        "6차 스킬": (145, 4400),
        "3rd 스킬": (110, 3302),
        "마스터리": (80, 2202),
        "5차 강화": (119, 3308),
        "공용": (201, 6143),
        "직업군 공용": (133, 3945),
    }


def test_calculate_hexa_cost_summary_matches_golden_values_for_5_to_30() -> None:
    assert profile_totals(5, 30) == {
        "6차 스킬": (140, 4250),
        "3rd 스킬": (106, 3191),
        "마스터리": (76, 2126),
        "5차 강화": (114, 3194),
        "공용": (192, 5954),
        "직업군 공용": (128, 3815),
    }


def test_calculate_hexa_cost_summary_matches_golden_values_for_6_to_21() -> None:
    assert profile_totals(6, 21) == {
        "6차 스킬": (73, 1980),
        "3rd 스킬": (55, 1480),
        "마스터리": (40, 991),
        "5차 강화": (60, 1489),
        "공용": (104, 2773),
        "직업군 공용": (67, 1772),
    }


def test_calculate_hexa_cost_summary_matches_internal_sanity_check_for_0_to_30() -> None:
    assert profile_totals(0, 30) == {
        "6차 스킬": (150, 4500),
        "3rd 스킬": (117, 3442),
        "마스터리": (83, 2252),
        "5차 강화": (123, 3383),
        "공용": (208, 6268),
        "직업군 공용": (137, 4035),
    }


def test_resolve_hexa_cost_profile_distinguishes_verified_mixed_profiles() -> None:
    assert resolve_hexa_cost_profile("데드 스페이스", "스킬 코어") == "6차 스킬"
    assert resolve_hexa_cost_profile("암영난참", "스킬 코어") == "3rd 스킬"
    assert resolve_hexa_cost_profile("드래곤 소어/버티컬 피니셔/소어-돌아와!", "스킬 코어") == "3rd 스킬"
    assert (
        resolve_hexa_cost_profile(
            "[발현] 스트라이크 임팩트/[처형] 팬텀 레퀴엠",
            "스킬 코어",
        )
        == "3rd 스킬"
    )
    assert resolve_hexa_cost_profile("다크 임페일 VI/다크 신서시스 VI", "마스터리 코어") == "마스터리"
    assert resolve_hexa_cost_profile("다크 스피어", "강화 코어") == "5차 강화"
    assert resolve_hexa_cost_profile("솔 야누스", "공용 코어") == "공용"
    assert resolve_hexa_cost_profile("이볼브 VI", "공용 코어") == "직업군 공용"
    assert resolve_hexa_cost_profile("블리츠 실드 VI/블리츠 버스트", "공용 코어") == "직업군 공용"
    assert resolve_hexa_cost_profile("얼티밋 다크 사이트 VI", "공용 코어") == "직업군 공용"


def test_calculate_hexa_cumulative_cost_includes_activation_cost_for_non_origin_skill_core() -> None:
    level_one = calculate_hexa_cumulative_cost([build_core("미등록 헥사 코어", 1, "스킬 코어")])
    level_twenty_nine = calculate_hexa_cumulative_cost([build_core("미등록 헥사 코어", 29, "스킬 코어")])
    level_thirty = calculate_hexa_cumulative_cost([build_core("미등록 헥사 코어", 30, "스킬 코어")])

    assert level_one.sol_erda is not None
    assert level_one.fragments is not None
    assert level_one.sol_erda.current == 5
    assert level_one.fragments.current == 100
    assert level_one.sol_erda.maximum == 150
    assert level_one.fragments.maximum == 4500

    assert level_twenty_nine.sol_erda is not None
    assert level_twenty_nine.fragments is not None
    assert level_twenty_nine.sol_erda.current == 130
    assert level_twenty_nine.fragments.current == 4000

    assert level_thirty.sol_erda is not None
    assert level_thirty.fragments is not None
    assert level_thirty.sol_erda.current == 150
    assert level_thirty.fragments.current == 4500
    assert level_thirty.sol_erda.percent == 100
    assert level_thirty.fragments.percent == 100


def test_calculate_hexa_cumulative_cost_excludes_free_origin_activation_from_current_only() -> None:
    summary = calculate_hexa_cumulative_cost([build_core("데드 스페이스", 30, "스킬 코어")])

    assert summary.sol_erda is not None
    assert summary.fragments is not None
    assert summary.sol_erda.current == 145
    assert summary.sol_erda.maximum == 150
    assert summary.sol_erda.percent == 96
    assert summary.fragments.current == 4400
    assert summary.fragments.maximum == 4500
    assert summary.fragments.percent == 97


def test_calculate_hexa_cumulative_cost_sums_multiple_verified_cores() -> None:
    summary = calculate_hexa_cumulative_cost(
        [
            build_core("데드 스페이스", 18, "스킬 코어"),
            build_core("다크 임페일 VI/다크 신서시스 VI", 30, "마스터리 코어"),
            build_core("다크 스피어", 30, "강화 코어"),
            build_core("솔 야누스", 30, "공용 코어"),
        ]
    )

    assert summary.sol_erda is not None
    assert summary.fragments is not None
    assert summary.sol_erda.current == 469
    assert summary.sol_erda.maximum == 564
    assert summary.sol_erda.percent == 83
    assert summary.fragments.current == 13403
    assert summary.fragments.maximum == 16403
    assert summary.fragments.percent == 81
    assert summary.unresolved_core_names == []


def test_calculate_hexa_cumulative_cost_adds_hexa_stat_activation_sol_erda_only() -> None:
    summary = calculate_hexa_cumulative_cost(
        [build_core("미등록 헥사 코어", 12, "스킬 코어")],
        [
            build_stat_set("HEXA 스탯 I"),
            build_stat_set("HEXA 스탯 II"),
            build_stat_set("HEXA 스탯 III"),
        ],
    )

    assert summary.sol_erda is not None
    assert summary.fragments is not None
    assert summary.sol_erda.current == 66
    assert summary.sol_erda.maximum == 150
    assert summary.sol_erda.percent == 44
    assert summary.fragments.current == 850
    assert summary.fragments.maximum == 4500
    assert summary.fragments.percent == 18
    assert summary.unresolved_core_names == []


def test_calculate_hexa_cumulative_cost_uses_existing_skill_profile_for_unregistered_skill_core() -> None:
    summary = calculate_hexa_cumulative_cost(
        [
            build_core("미등록 헥사 코어", 12, "스킬 코어"),
        ]
    )

    assert summary.sol_erda is not None
    assert summary.fragments is not None
    assert summary.sol_erda.current == 36
    assert summary.sol_erda.maximum == 150
    assert summary.sol_erda.percent == 24
    assert summary.fragments.current == 850
    assert summary.fragments.maximum == 4500
    assert summary.fragments.percent == 18
    assert summary.unresolved_core_names == []


def test_calculate_hexa_cumulative_cost_uses_common_profile_for_unregistered_common_core() -> None:
    summary = calculate_hexa_cumulative_cost(
        [
            build_core("가상의 일반 공용 코어", 9, "공용 코어"),
        ]
    )

    assert summary.sol_erda is not None
    assert summary.fragments is not None
    assert summary.sol_erda.current == 32
    assert summary.sol_erda.maximum == 208
    assert summary.sol_erda.percent == 15
    assert summary.fragments.current == 603
    assert summary.fragments.maximum == 6268
    assert summary.fragments.percent == 9
    assert summary.unresolved_core_names == []


def test_calculate_hexa_cumulative_cost_reports_unresolved_core_names_for_unknown_core_type() -> None:
    summary = calculate_hexa_cumulative_cost(
        [
            build_core("알 수 없는 코어", 12, "새로운 타입"),
        ]
    )

    assert summary.sol_erda is None
    assert summary.fragments is None
    assert summary.unresolved_core_names == ["알 수 없는 코어"]


def test_resolve_hexa_cost_profile_uses_safe_defaults_for_unregistered_skill_and_common_cores() -> None:
    assert resolve_hexa_cost_profile("가상의 일반 스킬 코어", "스킬 코어") == "6차 스킬"
    assert resolve_hexa_cost_profile("가상의 일반 공용 코어", "공용 코어") == "공용"


def test_resolve_hexa_cost_profile_returns_none_for_unknown_or_missing_type() -> None:
    assert resolve_hexa_cost_profile("알 수 없는 코어", "새로운 타입") is None
    assert resolve_hexa_cost_profile("알 수 없는 코어", None) is None
    assert resolve_hexa_cost_profile("", "스킬 코어") is None
