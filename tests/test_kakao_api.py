from __future__ import annotations

from app.api.kakao import KAKAO_SKILL_TOKEN_HEADER
from tests.api_test_support import (
    FakeHistoryCrawler,
    build_provider_timeout_error,
    build_test_app,
    request_json,
)


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
        json={"userRequest": {"utterance": "!환산 창킬"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "[창킬 환산주스탯]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
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
        json={"userRequest": {"utterance": "!환산 창킬"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "[창킬 환산주스탯]\n\nhttps://maplescouter.com/ko/info?name=%EC%B0%BD%ED%82%AC"
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
        json={"userRequest": {"utterance": "!환산 창킬"}},
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
        json={"userRequest": {"utterance": "!환산 창킬"}},
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
        json={"userRequest": {"utterance": "!경험치 히스토리 창킬"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
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


def test_kakao_webhook_valid_hexa_command_uses_shared_command_pipeline() -> None:
    app, history_crawler = build_test_app(kakao_skill_token="secret-token")

    response = request_json(
        app,
        "POST",
        "/kakao/webhook",
        headers={KAKAO_SKILL_TOKEN_HEADER: "secret-token"},
        json={"userRequest": {"utterance": "!헥사 창킬"}},
    )

    assert response.status_code == 200
    assert history_crawler.hexa_received_names == ["창킬"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": EXPECTED_HEXA_REPLY
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
        json={"userRequest": {"utterance": "!없는명령어 창킬"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "지원하지 않는 명령어입니다."
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
        json={"userRequest": {"utterance": "!환산"}},
    )

    assert response.status_code == 200
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "캐릭터명을 입력해주세요."
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
                        "text": "잘못된 요청입니다."
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
        json={"userRequest": {"utterance": "!경험치 히스토리 창킬"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
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
        json={"userRequest": {"utterance": "!경험치 히스토리 창킬"}},
    )

    assert response.status_code == 200
    assert history_crawler.received_names == ["창킬"]
    assert response.json() == {
        "version": "2.0",
        "template": {
            "outputs": [
                {
                    "simpleText": {
                        "text": "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
                    }
                }
            ]
        },
    }
