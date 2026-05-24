from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from .. import LLMConfig


class GetLLMConfigByNameResponse(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    config: LLMConfig | None


def get_llm_config_by_name(session: Session, name: str) -> GetLLMConfigByNameResponse:
    stmt = select(LLMConfig).where(LLMConfig.name == name)
    return GetLLMConfigByNameResponse(config=session.execute(stmt).scalar_one_or_none())
