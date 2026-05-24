from fastapi import APIRouter

from ..models import HealthResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    response_model_exclude_none=True,
)
def health() -> HealthResponse:
    return HealthResponse(status="ok")
