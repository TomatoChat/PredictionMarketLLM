from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import LLMConfig


class GetActiveLLMConfigNamesResponse(BaseModel):
    names: list[str]


def get_active_llm_config_names(session: Session) -> GetActiveLLMConfigNamesResponse:
    stmt = select(LLMConfig.name).where(LLMConfig.active.is_(True))
    return GetActiveLLMConfigNamesResponse(
        names=list(session.execute(stmt).scalars().all())
    )
