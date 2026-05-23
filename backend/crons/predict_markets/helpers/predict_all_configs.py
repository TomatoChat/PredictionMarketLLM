import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.crons.predict_markets.helpers.predict_with_config import (
    predict_with_config,
)
from backend.supabase.queries import get_active_llm_config_names
from settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def predict_all_configs(dry_run: bool = False) -> bool:
    """Run predictions for every active config across every active market.

    When ``dry_run`` is True, the providers are called but no rows are written.
    """
    try:
        engine = create_engine(settings.database_url)

        with Session(engine) as session:
            names = get_active_llm_config_names(session).names

        if not names:
            logger.warning("predict_all_configs - no active configs; nothing to do")
            return True

        return all(predict_with_config(name, dry_run=dry_run) for name in names)
    except Exception:
        logger.exception("predict_all_configs - failed")
        return False
