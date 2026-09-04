from __future__ import annotations

from fastapi import APIRouter, Response, status


router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get(
    "/ready",
    status_code=status.HTTP_204_NO_CONTENT,
    include_in_schema=False,
)
async def ready() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)
