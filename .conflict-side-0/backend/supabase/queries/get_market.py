from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from .. import Market


class GetMarketResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    market: Market | None


def get_market(session: Session, market_id: str) -> GetMarketResponse:
    return GetMarketResponse(market=session.get(Market, market_id))
