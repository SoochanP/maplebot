from __future__ import annotations

from app.api.kakao import KAKAO_SKILL_TOKEN_HEADER
from tests.api_test_support import (
    FakeHistoryCrawler,
    build_provider_timeout_error,
    build_test_app,
    request_json,
)


EXPECTED_HISTORY_REPLY = (
    "[\ucc3d\ud0ac] - \uc2a4\uce74\ub2c8\uc544\n\n"
    "01\uc6d4 11\uc77c : Lv.289 10.000%\n"
    "01\uc6d4 12\uc77c : Lv.289 12.500% (+250 EXP)\n\n"
    "\uc77c\uc77c \ud3c9\uade0 \ud68d\ub4dd\ub7c9: 250 EXP\n"
    "\ub0a8\uc740 \uacbd\ud5d8\uce58\ub7c9: 8,750 EXP\n"
    "\uc608\uc0c1 \ub808\ubca8\uc5c5 \ub0a0\uc9dc:\n"
    "25\ub144 02\uc6d4 16\uc77c (35\uc77c \ud6c4)"
)


def test_health_check_is_public() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(app, "GET", "/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_kakao_webhook_allows_requests_without_token_when_not_configured() -> None:
    app, _ = build_test_app()

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        json={"userRequest": {"utterance": "!\ud658\uc0b0 \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "[\ucc3d\ud0ac \ud658\uc0b0\uc8fc\uc2a4\ud0ef]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
                    }
                }
            ]
        },
    }


def test_kakao_webhook_accepts_correct_secret_header() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\ud658\uc0b0 \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "[\ucc3d\ud0ac \ud658\uc0b0\uc8fc\uc2a4\ud0ef]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
                    }
                }
            ]
        },
    }


def test_kakao_webhook_rejects_missing_secret_header() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        json={"userRequest": {"utterance": "!\ud658\uc0b0 \ucc3d\ud0ac"}},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_kakao_webhook_rejects_incorrect_secret_header() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "wrong-token"},
        json={"userRequest": {"utterance": "!\ud658\uc0b0 \ucc3d\ud0ac"}},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Unauthorized"}


def test_kakao_webhook_valid_experience_history_command() -> None:
    app, history_crawler = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": EXPECTED_HISTORY_REPLY
                    }
                }
            ]
        },
    }


def test_kakao_webhook_returns_user_friendly_error_for_unsupported_command() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\uc5c6\ub294\uba85\ub839\uc5b4 \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "\uc9c0\uc6d0\ud558\uc9c0 \uc54a\ub294 \uba85\ub839\uc5b4\uc785\ub2c8\ub2e4."
                    }
                }
            ]
        },
    }


def test_kakao_webhook_returns_user_friendly_error_for_missing_character_name() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\ud658\uc0b0"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "\uce90\ub9ad\ud130\uba85\uc744 \uc785\ub825\ud574\uc8fc\uc138\uc694."
                    }
                }
            ]
        },
    }


def test_kakao_webhook_rejects_malformed_payload() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {}},
    )

    assert response.status_code == 400
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "\uc798\ubabb\ub41c \uc694\uccad\uc785\ub2c8\ub2e4."
                    }
                }
            ]
        },
    }


def test_kakao_webhook_maps_external_provider_timeout_to_user_friendly_error() -> None:
    app, history_crawler = build_test_app(
        kakao_skill_token="secret-token",
        history_crawler=FakeHistoryCrawler(error=build_provider_timeout_error()),
    )

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "\ud604\uc7ac \uc870\ud68c \uc0ac\uc774\ud2b8\uc5d0 \uc811\uc18d\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
                    }
                }
            ]
        },
    }


def test_kakao_webhook_stops_slow_commands_before_skill_timeout() -> None:
    app, history_crawler = build_test_app(
        kakao_skill_token="secret-token",
        kakao_request_timeout_seconds=0.01,
        history_crawler=FakeHistoryCrawler(delay_seconds=0.05),
    )

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!\uacbd\ud5d8\uce58 \ud788\uc2a4\ud1a0\ub9ac \ucc3d\ud0ac"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["\ucc3d\ud0ac"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "\ud604\uc7ac \uc870\ud68c \uc0ac\uc774\ud2b8\uc5d0 \uc811\uc18d\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4.\n\uc7a0\uc2dc \ud6c4 \ub2e4\uc2dc \uc2dc\ub3c4\ud574\uc8fc\uc138\uc694."
                    }
                }
            ]
        },
    }