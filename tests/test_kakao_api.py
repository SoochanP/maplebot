from __future__ import annotations

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx

from app.api.kakao import KAKAO_SKILL_TOKEN_HEADER
from app.bootstrap import ApplicationServices
from app.commands.converted_stat import ConvertedStatCommand
from app.commands.experience_history import ExperienceHistoryCommand
from app.commands.router import CommandRouter
from app.core.exceptions import ExternalSiteUnavailableError
from app.core.http_client import HttpClientManager, HttpClientSettings
from app.core.settings import ApplicationSettings
from app.main import create_app
from app.models.experience_history import ExperienceHistory, ExperienceHistoryEntry
from app.services.maple_scouter_link import MapleScouterLinkBuilder


class FakeHistoryCrawler:
    def __init__(
        self,
        *,
        error: Exception | None = None,
        delay_seconds: float = 0.0,
    ) -> None:
        self._error = error
        self._delay_seconds = delay_seconds
        self.received_names: list[str] = []

    async def fetch_experience_history(self, character_name: str) -> ExperienceHistory:
        self.received_names.append(character_name)

        if self._delay_seconds > 0:
            await asyncio.sleep(self._delay_seconds)

        if self._error is not None:
            raise self._error

        return ExperienceHistory(
            character_name=character_name,
            entries=[
                ExperienceHistoryEntry(
                    date=date(2025, 1, 11),
                    snapshot_at=datetime(2025, 1, 11, tzinfo=timezone.utc),
                    level=289,
                    experience=1000,
                    experience_percent=Decimal("10.000"),
                ),
                ExperienceHistoryEntry(
                    date=date(2025, 1, 12),
                    snapshot_at=datetime(2025, 1, 12, tzinfo=timezone.utc),
                    level=289,
                    experience=1250,
                    experience_percent=Decimal("12.500"),
                ),
            ],
        )


def build_test_app(
    *,
    kakao_skill_token: str | None = None,
    kakao_request_timeout_seconds: float = 4.5,
    history_crawler: FakeHistoryCrawler | None = None,
):
    crawler = history_crawler or FakeHistoryCrawler()
    services = ApplicationServices(
        http_client_manager=HttpClientManager(settings=HttpClientSettings()),
        command_router=CommandRouter(
            handlers=[
                ConvertedStatCommand(MapleScouterLinkBuilder()),
                ExperienceHistoryCommand(crawler),
            ]
        ),
    )
    settings = ApplicationSettings(
        kakao_skill_token=kakao_skill_token,
        kakao_request_timeout_seconds=kakao_request_timeout_seconds,
    )
    app = create_app(services=services, settings=settings)
    return app, crawler


def request_json(
    app,
    method: str,
    path: str,
    *,
    headers: dict[str, str] | None = None,
    json: object | None = None,
) -> httpx.Response:
    async def run_request() -> httpx.Response:
        services = app.state.services
        await services.start()
        try:
            transport = httpx.ASGITransport(app=app)
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                return await client.request(
                    method,
                    path,
                    headers=headers,
                    json=json,
                )
        finally:
            await services.close()

    return asyncio.run(run_request())


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
                        "text": "[창킬 경험치 히스토리]\n\n01/11  Lv.289  10.000%\n01/12  Lv.289  12.500%  (+2.500%)\n\n최근 2개 기록 변화: +250 EXP (+2.500%)"
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
        history_crawler=FakeHistoryCrawler(
            error=ExternalSiteUnavailableError(
                "현재 조회 사이트에 접속할 수 없습니다.\n잠시 후 다시 시도해주세요."
            )
        ),
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
