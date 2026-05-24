from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import OutcomeSnapshot


class GetLatestOutcomePriceResponse(BaseModel):
    price: Decimal | None
    captured_at: datetime | None


def get_latest_outcome_price(
    session: Session, outcome_id: str, at: datetime | None = None
) -> GetLatestOutcomePriceResponse:
    """Return the ``outcome_snapshot`` row for ``outcome_id`` closest to but not after ``at``.

    When ``at`` is omitted, returns the most recent snapshot. Used at read time
    to recover the market-implied probability the picked outcome had at the
    moment of an ``llm_prediction`` — causally correct because we never look
    past the decision timestamp.
    """
    stmt = select(OutcomeSnapshot.price, OutcomeSnapshot.captured_at).where(
        OutcomeSnapshot.outcome_id == outcome_id
    )
    if at is not None:
        stmt = stmt.where(OutcomeSnapshot.captured_at <= at)
    stmt = stmt.order_by(OutcomeSnapshot.captured_at.desc()).limit(1)

    row = session.execute(stmt).one_or_none()
    if row is None:
        return GetLatestOutcomePriceResponse(price=None, captured_at=None)
    return GetLatestOutcomePriceResponse(price=row.price, captured_at=row.captured_at)
