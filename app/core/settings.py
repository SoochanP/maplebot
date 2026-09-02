from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.core.http_client import HttpClientSettings


class ApplicationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    kakao_skill_token: str | None = None
    bridge_token: str | None = None
    nexon_api_key: str | None = None
    kakao_request_timeout_seconds: float = Field(default=4.5, gt=0, le=5.0)
    command_execution_timeout_seconds: float = Field(default=15.0, gt=0, le=30.0)
    http_request_timeout_seconds: float = Field(default=8.0, gt=0, le=15.0)
    http_connect_timeout_seconds: float = Field(default=2.0, gt=0, le=5.0)

    @classmethod
    def from_env(cls) -> "ApplicationSettings":
        raw_values = {
            "kakao_skill_token": _read_optional_string_env("MAPLEBOT_KAKAO_SKILL_TOKEN"),
            "bridge_token": _read_optional_string_env("MAPLEBOT_BRIDGE_TOKEN"),
            "nexon_api_key": _read_optional_string_env("MAPLEBOT_NEXON_API_KEY"),
            "kakao_request_timeout_seconds": os.getenv("MAPLEBOT_KAKAO_REQUEST_TIMEOUT_SECONDS"),
            "command_execution_timeout_seconds": os.getenv(
                "MAPLEBOT_COMMAND_EXECUTION_TIMEOUT_SECONDS"
            ),
            "http_request_timeout_seconds": os.getenv("MAPLEBOT_HTTP_REQUEST_TIMEOUT_SECONDS"),
            "http_connect_timeout_seconds": os.getenv("MAPLEBOT_HTTP_CONNECT_TIMEOUT_SECONDS"),
        }
        filtered_values = {
            key: value
            for key, value in raw_values.items()
            if value is not None
        }
        return cls.model_validate(filtered_values)

    @model_validator(mode="after")
    def validate_timeouts(self) -> "ApplicationSettings":
        if self.http_connect_timeout_seconds > self.http_request_timeout_seconds:
            raise ValueError("HTTP connect timeout must not exceed HTTP request timeout.")

        if self.command_execution_timeout_seconds <= self.http_request_timeout_seconds:
            raise ValueError(
                "Command execution timeout must be greater than HTTP request timeout."
            )

        return self

    @property
    def http_client_settings(self) -> HttpClientSettings:
        return HttpClientSettings(
            request_timeout_seconds=self.http_request_timeout_seconds,
            connect_timeout_seconds=self.http_connect_timeout_seconds,
        )


def _read_optional_string_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None:
        return None

    stripped_value = value.strip()
    return stripped_value or None
