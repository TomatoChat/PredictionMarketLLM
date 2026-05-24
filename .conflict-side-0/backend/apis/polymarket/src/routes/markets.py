from itertools import islice
from typing import Annotated

from fastapi import APIRouter, Depends

from ..helpers.fetch_active_markets import fetch_active_markets
from ..models import ListMarketsRequest, ListMarketsResponse

router = APIRouter()


@router.get(
    "/markets",
    response_model=ListMarketsResponse,
    response_model_exclude_none=True,
)
def list_markets(
    request: Annotated[ListMarketsRequest, Depends()],
) -> ListMarketsResponse:
    """Return the first ``limit`` active Polymarket markets via the CLOB SDK."""
    markets = list(islice(fetch_active_markets(), request.limit))
    return ListMarketsResponse(markets=markets)
