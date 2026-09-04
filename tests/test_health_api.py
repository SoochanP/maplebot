from __future__ import annotations

from tests.api_test_support import build_test_app, request_json


def test_ready_check_returns_no_content_without_authentication() -> None:
    app, _ = build_test_app(kakao_skill_token="secret-token", bridge_token="bridge-secret")

    response = request_json(app, "GET", "/health/ready")

    assert response.status_code == 204
    assert response.content == b""
    assert response.text == ""


def test_ready_check_does_not_touch_command_providers() -> None:
    app, provider = build_test_app(kakao_skill_token="secret-token", bridge_token="bridge-secret")

    response = request_json(app, "GET", "/health/ready")

    assert response.status_code == 204
    assert provider.received_names == []
    assert provider.hexa_received_names == []
    assert provider.union_received_names == []
    assert provider.ranking_received_names == []
    assert provider.notice_limits == []
