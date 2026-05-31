from shared_models import PredictRequest
from fastapi import APIRouter, HTTPException
from settings import get_settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from db.queries import get_llm_config_by_name

from ..classes.PredictorLLM import PredictorLLM
from ..models import PredictResponse

router = APIRouter()


@router.post(
    "/predict",
    response_model=PredictResponse,
    response_model_exclude_none=True,
)
def predict(request: PredictRequest) -> PredictResponse:
    """Run one PredictorLLM cycle against the given market + config.

    ``PredictorLLM.predict`` handles its own commit on success, so the route
    just returns the boolean result.
    """
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

    return PredictResponse(success=success)
