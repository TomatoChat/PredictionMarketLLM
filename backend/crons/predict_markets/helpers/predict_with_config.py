import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tqdm import tqdm

from backend.llm.classes import PredictorLLM
from backend.supabase.queries import get_active_market_ids, get_llm_config_by_name
from settings import get_settings

logger = logging.getLogger(__name__)


def predict_with_config(config_name: str, market_id: str | None = None) -> bool:
    """Run predictions for ``config_name``.

    If ``market_id`` is given, predict that one market; otherwise iterate over
    every market with a today-dated active snapshot.
    """
    try:
        engine = create_engine(get_settings().database_url)

        with Session(engine) as session:
            config = get_llm_config_by_name(session, config_name).config

            if config is None:
                logger.error(f"predict_with_config - config {config_name} not found")
                return False

            if not config.active and market_id is None:
                logger.info(
                    f"predict_with_config - config {config_name} is inactive; skipping batch"
                )
                return True

            if market_id is not None:
                market_ids = [market_id]
            else:
                market_ids = get_active_market_ids(session).market_ids

            predictor = PredictorLLM(config)
            n_ok = 0
            n_failed = 0

            for mid in tqdm(market_ids, desc=f"predicting - {config_name}", unit="mkt"):
                if predictor.predict(mid, session):
                    n_ok += 1
                else:
                    n_failed += 1

        logger.info(
            f"predict_with_config - {config_name} done (ok={n_ok} failed={n_failed} total={len(market_ids)})"  # noqa: E501
        )
        return n_failed == 0
    except Exception:
        logger.exception(f"predict_with_config - {config_name} failed")
        return False
