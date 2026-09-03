from __future__ import annotations

from app.api.bridge import BRIDGE_TOKEN_HEADER
from tests.api_test_support import FakeHistoryCrawler, build_test_app, request_json


EXPECTED_HISTORY_REPLY = (
    "[창킬] - 스카니아\n\n"
    "01월 11일 : Lv.289 10.000%\n"
    "01월 12일 : Lv.289 12.500% (+250 EXP)\n\n"
    "일일 평균 획득량: 250 EXP\n"
    "남은 경험치량: 8,750 EXP\n"
    "예상 레벨업 날짜:\n"
    "25년 02월 16일 (35일 후)"
)

EXPECTED_HEXA_REPLY = (
    "[창킬] 헥사 스킬 정보\n\n"
    "• [스킬] Lv.18 데드 스페이스\n"
    "• [마스] Lv.30 다크 임페일 VI/다크 신서시스 VI\n"
    "• [강화] Lv.30 다크 스피어\n"
    "• [공용] Lv.30 솔 야누스\n\n"
    "• 누적 솔 에르다 : 474 / 564 (84%)\n"
    "• 누적 조각 : 13,503 / 16,403 (82%)"
)

EXPECTED_HEXA_COST_REPLY = (
    "[HEXA 강화 비용 1 → 30]\n\n"
    "6차 스킬\n"
    "솔 에르다: 145개 (기운 145,000)\n"
    "조각: 4,400개\n\n"
    "3rd 스킬\n"
    "솔 에르다: 110개 (기운 110,000)\n"
    "조각: 3,302개\n\n"
    "마스터리\n"
    "솔 에르다: 80개 (기운 80,000)\n"
    "조각: 2,202개\n\n"
    "5차 강화\n"
    "솔 에르다: 119개 (기운 119,000)\n"
    "조각: 3,308개\n\n"
    "공용\n"
    "솔 에르다: 201개 (기운 201,000)\n"
    "조각: 6,143개\n\n"
    "직업군 공용\n"
    "솔 에르다: 133개 (기운 133,000)\n"
    "조각: 3,945개"
)


def test_bridge_message_valid_converted_stat_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={
            "room": "메이플 단톡방",
            "sender": "사용자",
            "message": "!환산 창킬",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "[창킬 환산주스탯]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
    }


def test_bridge_message_valid_experience_history_command() -> None:
    app, history_crawler = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={
            "room": "메이플 단톡방",
            "sender": "사용자",
            "message": "!경험치 히스토리 창킬",
        },
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {"reply": EXPECTED_HISTORY_REPLY}


def test_bridge_message_valid_experience_history_alias_command() -> None:
    app, history_crawler = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!경험치 창킬"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {"reply": EXPECTED_HISTORY_REPLY}


def test_bridge_message_valid_hexa_command() -> None:
    app, provider = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!헥사 창킬"},
    )

    assert response.status_code == 200
    assert provider.hexa_received_names == ["창킬"]
    assert response.json() == {"reply": EXPECTED_HEXA_REPLY}


def test_bridge_message_valid_hexa_cost_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!헥사비용 1->30"},
    )

    assert response.status_code == 200
    assert response.json() == {"reply": EXPECTED_HEXA_COST_REPLY}


def test_bridge_message_valid_union_command() -> None:
    app, provider = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!유니온 창킬"},
    )

    assert response.status_code == 200
    assert provider.union_received_names == ["창킬"]
    assert response.json() == {
        "reply": "[창킬 유니온]\n\n유니온 레벨: 9,867\n유니온 등급: 그랜드 마스터 유니온 4\n아티팩트 레벨: 59\n아티팩트 포인트: 19,700\n잔여 아티팩트 AP: 6\n아티팩트 효과: 올스탯 150 증가\n\n유니온 챔피언\nSSS: 1명\n누적 효과: 크리티컬 데미지 12.00% 증가"
    }


def test_bridge_message_returns_user_friendly_error_for_unsupported_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!없는명령어 창킬"},
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "지원하지 않는 명령어입니다."}


def test_bridge_message_rejects_missing_message() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"room": "테스트방", "sender": "테스터"},
    )

    assert response.status_code == 400
    assert response.json() == {"reply": "잘못된 요청입니다."}


def test_bridge_message_accepts_valid_bridge_token() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!환산 창킬"},
    )

    assert response.status_code == 200


def test_bridge_message_rejects_missing_bridge_token() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        json={"message": "!환산 창킬"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_bridge_message_rejects_invalid_bridge_token() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "wrong-token"},
        json={"message": "!환산 창킬"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_bridge_message_uses_command_timeout_instead_of_kakao_timeout() -> None:
    app, history_crawler = build_test_app(
        bridge_token="bridge-secret",
        kakao_request_timeout_seconds=0.01,
        command_execution_timeout_seconds=1.0,
        http_request_timeout_seconds=0.001,
        http_connect_timeout_seconds=0.001,
        history_crawler=FakeHistoryCrawler(delay_seconds=0.05),
    )

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!경험치 히스토리 창킬"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {"reply": EXPECTED_HISTORY_REPLY}


def test_bridge_message_maps_command_timeout_to_user_friendly_error() -> None:
    app, history_crawler = build_test_app(
        bridge_token="bridge-secret",
        command_execution_timeout_seconds=0.01,
        http_request_timeout_seconds=0.001,
        http_connect_timeout_seconds=0.001,
        history_crawler=FakeHistoryCrawler(delay_seconds=0.05),
    )

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!경험치 히스토리 창킬"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {
        "reply": "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
    }

