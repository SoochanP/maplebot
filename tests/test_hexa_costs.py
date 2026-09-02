from __future__ import annotations

from app.data.hexa_costs import calculate_hexa_cost_summary



def profile_totals(current_level: int, target_level: int) -> dict[str, tuple[int, int]]:
    summary = calculate_hexa_cost_summary(current_level, target_level)
    return {
        profile.profile_name: (profile.sol_erda, profile.fragments)
        for profile in summary.profiles
    }


def test_calculate_hexa_cost_summary_matches_golden_values_for_1_to_30() -> None:
    assert profile_totals(1, 30) == {
        "6\ucc28 \uc2a4\ud0ac": (145, 4400),
        "3rd \uc2a4\ud0ac": (110, 3302),
        "\ub9c8\uc2a4\ud130\ub9ac": (80, 2202),
        "5\ucc28 \uac15\ud654": (119, 3308),
        "\uacf5\uc6a9": (201, 6143),
        "\uc9c1\uc5c5\uad70 \uacf5\uc6a9": (133, 3945),
    }


def test_calculate_hexa_cost_summary_matches_golden_values_for_5_to_30() -> None:
    assert profile_totals(5, 30) == {
        "6\ucc28 \uc2a4\ud0ac": (140, 4250),
        "3rd \uc2a4\ud0ac": (106, 3191),
        "\ub9c8\uc2a4\ud130\ub9ac": (76, 2126),
        "5\ucc28 \uac15\ud654": (114, 3194),
        "\uacf5\uc6a9": (192, 5954),
        "\uc9c1\uc5c5\uad70 \uacf5\uc6a9": (128, 3815),
    }


def test_calculate_hexa_cost_summary_matches_golden_values_for_6_to_21() -> None:
    assert profile_totals(6, 21) == {
        "6\ucc28 \uc2a4\ud0ac": (73, 1980),
        "3rd \uc2a4\ud0ac": (55, 1480),
        "\ub9c8\uc2a4\ud130\ub9ac": (40, 991),
        "5\ucc28 \uac15\ud654": (60, 1489),
        "\uacf5\uc6a9": (104, 2773),
        "\uc9c1\uc5c5\uad70 \uacf5\uc6a9": (67, 1772),
    }


def test_calculate_hexa_cost_summary_matches_internal_sanity_check_for_0_to_30() -> None:
    assert profile_totals(0, 30) == {
        "6\ucc28 \uc2a4\ud0ac": (150, 4500),
        "3rd \uc2a4\ud0ac": (117, 3442),
        "\ub9c8\uc2a4\ud130\ub9ac": (83, 2252),
        "5\ucc28 \uac15\ud654": (123, 3383),
        "\uacf5\uc6a9": (208, 6268),
        "\uc9c1\uc5c5\uad70 \uacf5\uc6a9": (137, 4035),
    }