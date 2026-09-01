from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from app.core.http_client import HttpClientSettings


class ApplicationSettings(BaseModel):
    model_config = ConfigDict(frozen=True)

    kakao_skill_token: str | None = None
    kakao_request_timeout_seconds: float = Field(default=4.5, gt=0, le=5.0)
    http_request_timeout_seconds: float = Field(default=3.0, gt=0, le=4.5)
    http_connect_timeout_seconds: float = Field(default=1.0, gt=0, le=3.0)

    @classmethod
    def from_env(cls) -> "ApplicationSettings":
        raw_values = {
            "kakao_skill_token": _read_optional_string_env("MAPLEBOT_KAKAO_SKILL_TOKEN"),
            "kakao_request_timeout_seconds": os.getenv("MAPLEBOT_KAKAO_REQUEST_TIMEOUT_SECONDS"),
            "http_request_timeout_seconds": os.getenv("MAPLEBOT_HTTP_REQUEST_TIMEOUT_SECONDS"),
            "http_connect_timeout_seconds": os.getenv("MAPLEBOT_HTTP_CONNECT_TIMEOUT_SECONDS"),
        }
        filtered_values = {
            key: value
            for key, value in raw_values.items()
            if value is not None
        }
        return cls.model_validate(filtered_values)

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
