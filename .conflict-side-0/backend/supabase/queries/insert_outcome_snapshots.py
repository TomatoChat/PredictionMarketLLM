from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import OutcomeSnapshot


class InsertOutcomeSnapshotsResponse(BaseModel):
    count: int


def insert_outcome_snapshots(
    session: Session, rows: list[OutcomeSnapshot]
) -> InsertOutcomeSnapshotsResponse:
    """Append-only insert of outcome_snapshot rows. Idempotent on (outcome_id, captured_at)."""
    if not rows:
        return InsertOutcomeSnapshotsResponse(count=0)
    stmt = insert(OutcomeSnapshot).values(
        [{k: v for k, v in row.model_dump().items() if v is not None} for row in rows]
    )
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["outcome_id", "captured_at"],
    )
    session.execute(stmt)
    return InsertOutcomeSnapshotsResponse(count=len(rows))
