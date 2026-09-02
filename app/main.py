from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.bridge import router as bridge_router
from app.api.kakao import router as kakao_router
from app.bootstrap import ApplicationServices, build_application_services
from app.core.settings import ApplicationSettings


logger = logging.getLogger("maplebot.app")
ApplicationServicesFactory = Callable[[], ApplicationServices]


def create_lifespan(
    services_factory: ApplicationServicesFactory,
    *,
    settings: ApplicationSettings,
):
    @asynccontextmanager
    async def app_lifespan(app: FastAPI) -> AsyncIterator[None]:
        if settings.kakao_skill_token is None:
            logger.warning("kakao_webhook_auth=disabled reason=missing_skill_token")

        if settings.bridge_token is None:
            logger.warning("bridge_auth=disabled reason=missing_bridge_token")

        services = services_factory()
        app.state.services = services
        await services.start()
        try:
            yield
        finally:
            await services.close()

    return app_lifespan


def create_app(
    *,
    services: ApplicationServices | None = None,
    settings: ApplicationSettings | None = None,
) -> FastAPI:
    application_settings = settings or ApplicationSettings.from_env()

    if services is None:
        services_factory: ApplicationServicesFactory = lambda: build_application_services(
            settings=application_settings,
        )
    else:
        services_factory = lambda: services

    app = FastAPI(
        title="MapleBot",
        version="0.1.0",
        lifespan=create_lifespan(services_factory, settings=application_settings),
    )
    app.state.settings = application_settings
    if services is not None:
        app.state.services = services

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(kakao_router)
    app.include_router(bridge_router)
    return app


app = create_app()
