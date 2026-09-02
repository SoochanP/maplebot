from __future__ import annotations

import asyncio
from dataclasses import dataclass
import secrets

from fastapi import Request

from app.commands.router import CommandRouter
from app.core.exceptions import ExternalSiteUnavailableError, MapleBotError
from app.core.settings import ApplicationSettings


COMMAND_TIMEOUT_MESSAGE = (
    "현재 조회 사이트에 접속할 수 없습니다.\n"
    "잠시 후 다시 시도해주세요."
)


@dataclass(slots=True, frozen=True)
class CommandExecutionResult:
    reply_text: str
    command_name: str | None
    success: bool
    error_category: str | None = None


def get_command_router(request: Request) -> CommandRouter:
    return request.app.state.services.command_router


def get_application_settings(request: Request) -> ApplicationSettings:
    return request.app.state.settings


def has_valid_configured_token(
    *,
    provided_token: str | None,
    expected_token: str | None,
) -> bool:
    if expected_token is None:
        return True

    if provided_token is None:
        return False

    return secrets.compare_digest(provided_token, expected_token)


async def execute_command_text(
    command_router: CommandRouter,
    raw_text: str,
    *,
    timeout_seconds: float,
) -> CommandExecutionResult:
    command_name = command_router.peek_command_name(raw_text)

    try:
        async with asyncio.timeout(timeout_seconds):
            reply_text = await command_router.dispatch(raw_text)
    except TimeoutError:
        timeout_error = ExternalSiteUnavailableError(COMMAND_TIMEOUT_MESSAGE)
        return CommandExecutionResult(
            reply_text=timeout_error.user_message,
            command_name=command_name,
            success=False,
            error_category="TimeoutError",
        )
    except MapleBotError as exc:
        return CommandExecutionResult(
            reply_text=exc.user_message,
            command_name=command_name,
            success=False,
            error_category=type(exc).__name__,
        )

    return CommandExecutionResult(
        reply_text=reply_text,
        command_name=command_name,
        success=True,
    )
