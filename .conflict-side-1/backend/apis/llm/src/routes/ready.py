from fastapi import APIRouter

from ..models import ReadyResponse

router = APIRouter()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    response_model_exclude_none=True,
)
def ready() -> ReadyResponse:
    return ReadyResponse(status="ready")
