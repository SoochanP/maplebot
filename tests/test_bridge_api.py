from __future__ import annotations

from app.api.bridge import BRIDGE_TOKEN_HEADER
from tests.api_test_support import build_test_app, request_json


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
    assert response.json() == {
        "reply": "[창킬 경험치 히스토리]\n\n01/11  Lv.289  10.000%\n01/12  Lv.289  12.500%  (+2.500%)\n\n최근 2개 기록 변화: +250 EXP (+2.500%)"
    }


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
    assert response.json() == {
        "reply": "[창킬 HEXA]\n\nHEXA 코어\n[스킬 코어]\n- 데드 스페이스 Lv.18\n\nHEXA 스탯\n- I: 공격력 증가 Lv.8"
    }


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
