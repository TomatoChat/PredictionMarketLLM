from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import LLMConfig


class GetActiveLLMConfigsResponse(BaseModel):
    # (id, name) of each active config. id is needed for task naming; name is
    # the contract the predict handler looks the config up by.
    configs: list[tuple[str, str]]


def get_active_llm_configs(session: Session) -> GetActiveLLMConfigsResponse:
    stmt = select(LLMConfig.id, LLMConfig.name).where(LLMConfig.active.is_(True))
    return GetActiveLLMConfigsResponse(
        configs=[(row.id, row.name) for row in session.execute(stmt)]
    )
