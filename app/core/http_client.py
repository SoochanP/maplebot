from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass(slots=True, frozen=True)
class HttpClientSettings:
    request_timeout_seconds: float = 8.0
    connect_timeout_seconds: float = 2.0
    follow_redirects: bool = True
    user_agent: str = "MapleBot/0.1"

    @property
    def timeout(self) -> httpx.Timeout:
        return httpx.Timeout(
            timeout=self.request_timeout_seconds,
            connect=self.connect_timeout_seconds,
        )


class HttpClientManager:
    def __init__(
        self,
        *,
        settings: HttpClientSettings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._settings = settings
        self._transport = transport
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("HTTP client has not been started.")
        return self._client

    async def start(self) -> None:
        if self._client is not None:
            return

        self._client = httpx.AsyncClient(
            follow_redirects=self._settings.follow_redirects,
            timeout=self._settings.timeout,
            transport=self._transport,
            headers={"User-Agent": self._settings.user_agent},
        )

    async def close(self) -> None:
        if self._client is None:
            return

        await self._client.aclose()
        self._client = None
