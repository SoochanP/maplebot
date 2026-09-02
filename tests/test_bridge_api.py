from __future__ import annotations

from app.api.bridge import BRIDGE_TOKEN_HEADER
from tests.api_test_support import FakeHistoryCrawler, build_test_app, request_json


EXPECTED_HISTORY_REPLY = (
    "[\ucc3d\ud0ac] - \uc2a4\uce74\ub2c8\uc544\n\n"
    "01\uc6d4 11\uc77c : Lv.289 10.000%\n"
    "01\uc6d4 12\uc77c : Lv.289 12.500% (+250 EXP)\n\n"
    "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 250 EXP\n"
    "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 8,750 EXP\n"
    "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
    "25\ub144 02\uc6d4 16\uc77c (35\uc77c \ud6c4)"
)

EXPECTED_HEXA_COST_REPLY = (
    "[HEXA \uac15\ud654 \ube44\uc6a9 1 \u2192 30]\n\n"
    "6\ucc28 \uc2a4\ud0ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 145\uac1c (\uae30\uc6b4 145,000)\n"
    "\uc870\uac01: 4,400\uac1c\n\n"
    "3rd \uc2a4\ud0ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 110\uac1c (\uae30\uc6b4 110,000)\n"
    "\uc870\uac01: 3,302\uac1c\n\n"
    "\ub9c8\uc2a4\ud130\ub9ac\n"
    "\uc194 \uc5d0\ub974\ub2e4: 80\uac1c (\uae30\uc6b4 80,000)\n"
    "\uc870\uac01: 2,202\uac1c\n\n"
    "5\ucc28 \uac15\ud654\n"
    "\uc194 \uc5d0\ub974\ub2e4: 119\uac1c (\uae30\uc6b4 119,000)\n"
    "\uc870\uac01: 3,308\uac1c\n\n"
    "\uacf5\uc6a9\n"
    "\uc194 \uc5d0\ub974\ub2e4: 201\uac1c (\uae30\uc6b4 201,000)\n"
    "\uc870\uac01: 6,143\uac1c\n\n"
    "\uc9c1\uc5c5\uad70 \uacf5\uc6a9\n"
    "\uc194 \uc5d0\ub974\ub2e4: 133\uac1c (\uae30\uc6b4 133,000)\n"
    "\uc870\uac01: 3,945\uac1c"
)


def test_bridge_message_valid_converted_stat_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={
            "room": "\uba54\uc774\ud50c \ub2e8\ud1a1\ubc29",
            "sender": "\uc0ac\uc6a9\uc790",
            "message": "!\ud658\uc0b0 \ucc3d\ud0ac",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "reply": "[\ucc3d\ud0ac \ud658\uc0b0\uc8fc\uc2a4\ud0ef]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
    }


def test_bridge_message_valid_experience_history_command() -> None:
    app, history_crawler = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={
            "room": "\uba54\uc774\ud50c \ub2e8\ud1a1\ubc29",
            "sender": "\uc0ac\uc6a9\uc790",
            "message": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac",
        },
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {"reply": EXPECTED_HISTORY_REPLY}


def test_bridge_message_valid_experience_history_alias_command() -> None:
    app, history_crawler = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!\uacbd\ud5d8\uce58 \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {"reply": EXPECTED_HISTORY_REPLY}


def test_bridge_message_valid_hexa_command() -> None:
    app, provider = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!\ud5e5\uc0ac \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert provider.hexa_received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "reply": "[\ucc3d\ud0ac HEXA]\n\nHEXA \ucf54\uc5b4\n[\uc2a4\ud0ac \ucf54\uc5b4]\n- \ub370\ub4dc \uc2a4\ud398\uc774\uc2a4 Lv.18\n\nHEXA \uc2a4\ud0ef\n- I: \uacf5\uaca9\ub825 \uc99d\uac00 Lv.8"
    }


def test_bridge_message_valid_hexa_cost_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!\ud5e5\uc0ac\ube44\uc6a9 1->30"},
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
        json={"message": "!\uc720\ub2c8\uc628 \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert provider.union_received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "reply": "[\ucc3d\ud0ac \uc720\ub2c8\uc628]\n\n\uc720\ub2c8\uc628 \ub808\ubca8: 9,867\n\uc720\ub2c8\uc628 \ub4f1\uae09: \uadf8\ub79c\ub4dc \ub9c8\uc2a4\ud130 \uc720\ub2c8\uc628 4\n\uc544\ud2f0\ud329\ud2b8 \ub808\ubca8: 59\n\uc544\ud2f0\ud329\ud2b8 \ud3ec\uc778\ud2b8: 19,700\n\uc794\uc5ec \uc544\ud2f0\ud329\ud2b8 AP: 6\n\uc544\ud2f0\ud329\ud2b8 \ud6a8\uacfc: \uc62c\uc2a4\ud0ef 150 \uc99d\uac00\n\n\uc720\ub2c8\uc628 \ucc54\ud53c\uc5b8\nSSS: 1\uba85\n\ub204\uc801 \ud6a8\uacfc: \ud06c\ub9ac\ud2f0\uceec \ub370\ubbf8\uc9c0 12.00% \uc99d\uac00"
    }


def test_bridge_message_returns_user_friendly_error_for_unsupported_command() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!\uc5c6\ub294\uba85\ub839\uc5b4 \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert response.json() == {"reply": "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."}


def test_bridge_message_rejects_missing_message() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"room": "\ud14c\uc2a4\ud2b8\ubc29", "sender": "\ud14c\uc2a4\ud130"},
    )

    assert response.status_code == 400
    assert response.json() == {"reply": "\uc798\ubabb\ub41c \uc694\uccad\uc785\ub2c8\ub2e4."}


def test_bridge_message_accepts_valid_bridge_token() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        headers={BRIDGE_TOKEN_HEADER: "bridge-secret"},
        json={"message": "!\ud658\uc0b0 \ucc3d\ud0ac"},
    )

    assert response.status_code == 200


def test_bridge_message_rejects_missing_bridge_token() -> None:
    app, _ = build_test_app(bridge_token="bridge-secret")

    response = request_json(
        app,
        "POST",
        "/bridge/message",
        json={"message": "!\ud658\uc0b0 \ucc3d\ud0ac"},
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
        json={"message": "!\ud658\uc0b0 \ucc3d\ud0ac"},
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
        json={"message": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
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
        json={"message": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "reply": "\ud604\uc7ac \uc870\ud68c \uc0ac\uc774\ud2b8\uc5d0 \uc811\uc18d\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
    }
