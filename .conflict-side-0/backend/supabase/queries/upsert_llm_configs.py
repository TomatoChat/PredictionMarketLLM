from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from .. import LLMConfig


class UpsertLLMConfigsResponse(BaseModel):
    count: int


def upsert_llm_configs(
    session: Session, rows: list[LLMConfig]
) -> UpsertLLMConfigsResponse:
    """Insert llm_config rows, refreshing every mutable field on conflict (id)."""
    if not rows:
        return UpsertLLMConfigsResponse(count=0)
    values = [
        {k: v for k, v in row.model_dump().items() if v is not None} for row in rows
    ]
    stmt = insert(LLMConfig).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "provider": stmt.excluded.provider,
            "model": stmt.excluded.model,
            "model_snapshot": stmt.excluded.model_snapshot,
            "temperature": stmt.excluded.temperature,
            "top_p": stmt.excluded.top_p,
            "max_tokens": stmt.excluded.max_tokens,
            "tools": stmt.excluded.tools,
            "extra": stmt.excluded.extra,
            "active": stmt.excluded.active,
        },
    )
    session.execute(stmt)
    return UpsertLLMConfigsResponse(count=len(rows))
