from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import Outcome


class UpsertOutcomesResponse(BaseModel):
    count: int


def upsert_outcomes(session: Session, rows: list[Outcome]) -> UpsertOutcomesResponse:
    """Insert outcomes, updating mutable fields on conflict (id)."""
    if not rows:
        return UpsertOutcomesResponse(count=0)
    stmt = insert(Outcome).values([row.model_dump() for row in rows])
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "label": stmt.excluded.label,
            "market_winner": stmt.excluded.market_winner,
        },
    )
    session.execute(stmt)
    return UpsertOutcomesResponse(count=len(rows))
