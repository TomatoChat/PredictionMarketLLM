from typing import cast

from pydantic import BaseModel
from sqlalchemy import CursorResult, update
from sqlalchemy.orm import Session

from .. import LLMConfig


class DeactivateLLMConfigsExceptResponse(BaseModel):
    count: int


def deactivate_llm_configs_except(
    session: Session, keep_ids: list[str]
) -> DeactivateLLMConfigsExceptResponse:
    """Flip ``active = false`` on every llm_config whose id is not in ``keep_ids``.

    Lets the canonical set in ``PredictorLLM.canonical_configs()`` act as the
    source of truth: a config dropped from that list is retired here instead of
    via a hand-written migration. Rows are deactivated, never deleted, so the
    append-only ``llm_prediction`` history they own is preserved (no cascade).
    """
    stmt = update(LLMConfig).where(LLMConfig.active.is_(True)).values(active=False)
    if keep_ids:
        stmt = stmt.where(LLMConfig.id.not_in(keep_ids))

    result = cast(CursorResult[None], session.execute(stmt))
    return DeactivateLLMConfigsExceptResponse(count=result.rowcount or 0)
