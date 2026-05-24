from fastapi import APIRouter, HTTPException
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from supabase.queries import get_llm_config_by_name

from ..classes import PredictorLLM
from ..models import PredictRequest, PredictResponse

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictResponse,
    response_model_exclude_none=True,
)
def predict(request: PredictRequest) -> PredictResponse:
    """Run one PredictorLLM cycle against the given market + config."""
    engine = create_engine(get_settings().database_url)

    with Session(engine) as session:
        config_result = get_llm_config_by_name(session, request.config_name)

        if config_result.config is None:
            raise HTTPException(
                status_code=404,
                detail=f"config {request.config_name!r} not found",
            )

        predictor = PredictorLLM(config_result.config)
        success = predictor.predict(
            request.market_id, session, dry_run=request.dry_run
        )

        if not request.dry_run and success:
            session.commit()

    return PredictResponse(success=success)
