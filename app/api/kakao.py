from __future__ import annotations

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, StrictStr, ValidationError

from app.api.common import (
    execute_command_text,
    get_application_settings,
    get_command_router,
    has_valid_configured_token,
)
from app.commands.router import CommandRouter
from app.core.settings import ApplicationSettings


router = APIRouter(prefix="/kakao", tags=["kakao"])
logger = logging.getLogger("maplebot.kakao")
KAKAO_SKILL_TOKEN_HEADER = "X-MapleBot-Token"


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


def build_kakao_json_response(
    response: KakaoWebhookResponse,
    *,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(by_alias=True),
    )


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

    if not has_valid_configured_token(
        provided_token=request.headers.get(KAKAO_SKILL_TOKEN_HEADER),
        expected_token=settings.kakao_skill_token,
    ):
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

    execution_result = await execute_command_text(
        command_router,
        webhook_request.user_request.utterance,
        timeout_seconds=settings.kakao_request_timeout_seconds,
    )

    if execution_result.success:
        log_kakao_webhook(
            outcome="success",
            started_at=started_at,
            command_name=execution_result.command_name,
        )
    else:
        log_kakao_webhook(
            outcome="application_error",
            started_at=started_at,
            command_name=execution_result.command_name,
            error_category=execution_result.error_category,
        )

    return KakaoResponseBuilder.simple_text(execution_result.reply_text)
