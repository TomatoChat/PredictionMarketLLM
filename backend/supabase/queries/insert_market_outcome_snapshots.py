from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import MarketOutcomeSnapshot


class InsertMarketOutcomeSnapshotsResponse(BaseModel):
    count: int


def insert_market_outcome_snapshots(
    session: Session, rows: list[MarketOutcomeSnapshot]
) -> InsertMarketOutcomeSnapshotsResponse:
    """Append-only insert of market_outcome_snapshot rows.

    Idempotent on (outcome_id, captured_at).
    """
    if not rows:
        return InsertMarketOutcomeSnapshotsResponse(count=0)
    # Emit every column for every row (do NOT strip None): nullable price/volume/
    # liquidity legitimately vary across rows in one batch, and a multi-row insert
    # requires a homogeneous column set. captured_at is always set by the caller,
    # so dropping its server_default is moot here.
    stmt = insert(MarketOutcomeSnapshot).values([row.model_dump() for row in rows])
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["outcome_id", "captured_at"],
    )
    session.execute(stmt)
    return InsertMarketOutcomeSnapshotsResponse(count=len(rows))
