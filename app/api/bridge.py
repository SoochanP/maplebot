from __future__ import annotations

import logging
import time
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, StrictStr, ValidationError

from app.api.common import (
    execute_command_text,
    get_application_settings,
    get_command_router,
    has_valid_configured_token,
)
from app.commands.router import CommandRouter
from app.core.settings import ApplicationSettings


router = APIRouter(prefix="/bridge", tags=["bridge"])
logger = logging.getLogger("maplebot.bridge")
BRIDGE_TOKEN_HEADER = "X-MapleBot-Bridge-Token"


class BridgeMessageRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    room: str | None = None
    sender: str | None = None
    message: StrictStr


class BridgeMessageResponse(BaseModel):
    reply: str


def build_bridge_json_response(
    response: BridgeMessageResponse,
    *,
    status_code: int = status.HTTP_200_OK,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=response.model_dump(),
    )


def log_bridge_message(
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

    logger.info("bridge_message %s", " ".join(parts))


@router.post("/message", response_model=BridgeMessageResponse)
async def bridge_message(
    request: Request,
    payload: Annotated[Any, Body()],
    command_router: Annotated[CommandRouter, Depends(get_command_router)],
    settings: Annotated[ApplicationSettings, Depends(get_application_settings)],
) -> BridgeMessageResponse | JSONResponse:
    started_at = time.perf_counter()

    if not has_valid_configured_token(
        provided_token=request.headers.get(BRIDGE_TOKEN_HEADER),
        expected_token=settings.bridge_token,
    ):
        log_bridge_message(
            outcome="unauthorized",
            started_at=started_at,
            error_category="Unauthorized",
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": "Unauthorized"},
        )

    try:
        bridge_request = BridgeMessageRequest.model_validate(payload)
    except ValidationError:
        log_bridge_message(
            outcome="bad_request",
            started_at=started_at,
            error_category="ValidationError",
        )
        return build_bridge_json_response(
            BridgeMessageResponse(reply="잘못된 요청입니다."),
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    execution_result = await execute_command_text(
        command_router,
        bridge_request.message,
        timeout_seconds=settings.command_execution_timeout_seconds,
    )

    if execution_result.success:
        log_bridge_message(
            outcome="success",
            started_at=started_at,
            command_name=execution_result.command_name,
        )
    else:
        log_bridge_message(
            outcome="application_error",
            started_at=started_at,
            command_name=execution_result.command_name,
            error_category=execution_result.error_category,
        )

    return BridgeMessageResponse(reply=execution_result.reply_text)
