from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

from app.commands.router import CommandRouter
from app.core.exceptions import ExternalSiteUnavailableError, MapleBotError
from app.core.settings import ApplicationSettings


router = APIRouter(prefix="/kakao", tags=["kakao"])
logger = logging.getLogger("maplebot.kakao")
KAKAO_SKILL_TOKEN_HEADER = "X-MapleBot-Token"
KAKAO_TIMEOUT_MESSAGE = (
    "현재 조회 사이트에 접속할 수 없습니다.\n"
    "잠시 후 다시 시도해주세요."
)


class KakaoUserRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    utterance: StrictStr


class KakaoWebhookRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_request: KakaoUserRequest = Field(alias="userRequest")


class KakaoSimpleText(BaseModel):
    text: str


class KakaoOutput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    simple_text: KakaoSimpleText = Field(alias="simpleText")


class KakaoTemplate(BaseModel):
    outputs: list[KakaoOutput]


class KakaoWebhookResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version: str = "2.0"
    template: KakaoTemplate


class KakaoResponseBuilder:
    @staticmethod
    def simple_text(text: str) -> KakaoWebhookResponse:
        return KakaoWebhookResponse(
            template=KakaoTemplate(
                outputs=[
                    KakaoOutput(
                        simple_text=KakaoSimpleText(text=text),
                    )
                ]
            )
        )


def get_command_router(request: Request) -> CommandRouter:
    return request.app.state.services.command_router


def get_application_settings(request: Request) -> ApplicationSettings:
    return request.app.state.settings


def build_kakao_json_response(
    response: KakaoWebhookResponse,
    *,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(by_alias=True),
    )


def has_valid_kakao_token(request: Request, settings: ApplicationSettings) -> bool:
    expected_token = settings.kakao_skill_token
    if expected_token is None:
        return True

    provided_token = request.headers.get(KAKAO_SKILL_TOKEN_HEADER)
    if provided_token is None:
        return False

    return secrets.compare_digest(provided_token, expected_token)


def log_kakao_webhook(
    *,
    outcome: str,
    started_at: float,
    command_name: str | None = None,
    error_category: str | None = None,
) -> None:
    duration_ms = round((time.perf_counter() - started_at) * 1000)
    parts = [
        f"outcome={outcome}",
        f"duration_ms={duration_ms}",
    ]
    if command_name is not None:
        parts.append(f"command={command_name}")
    if error_category is not None:
        parts.append(f"error_category={error_category}")

    logger.info("kakao_webhook %s", " ".join(parts))


@router.post("/webhook", response_model=KakaoWebhookResponse)
async def kakao_webhook(
    request: Request,
    payload: Annotated[Any, Body()],
    command_router: Annotated[CommandRouter, Depends(get_command_router)],
    settings: Annotated[ApplicationSettings, Depends(get_application_settings)],
) -> KakaoWebhookResponse | JSONResponse:
    started_at = time.perf_counter()

    if not has_valid_kakao_token(request, settings):
        log_kakao_webhook(
            outcome="unauthorized",
            started_at=started_at,
            error_category="Unauthorized",
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Unauthorized"},
        )

    try:
        webhook_request = KakaoWebhookRequest.model_validate(payload)
    except ValidationError:
        log_kakao_webhook(
            outcome="bad_request",
            started_at=started_at,
            error_category="ValidationError",
        )
        return build_kakao_json_response(
            KakaoResponseBuilder.simple_text("잘못된 요청입니다."),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    command_name = command_router.peek_command_name(webhook_request.user_request.utterance)

    try:
        async with asyncio.timeout(settings.kakao_request_timeout_seconds):
            response_text = await command_router.dispatch(webhook_request.user_request.utterance)
    except TimeoutError:
        timeout_error = ExternalSiteUnavailableError(KAKAO_TIMEOUT_MESSAGE)
        log_kakao_webhook(
            outcome="application_error",
            started_at=started_at,
            command_name=command_name,
            error_category="TimeoutError",
        )
        return KakaoResponseBuilder.simple_text(timeout_error.user_message)
    except MapleBotError as exc:
        log_kakao_webhook(
            outcome="application_error",
            started_at=started_at,
            command_name=command_name,
            error_category=type(exc).__name__,
        )
        return KakaoResponseBuilder.simple_text(exc.user_message)

    log_kakao_webhook(
        outcome="success",
        started_at=started_at,
        command_name=command_name,
    )
    return KakaoResponseBuilder.simple_text(response_text)
