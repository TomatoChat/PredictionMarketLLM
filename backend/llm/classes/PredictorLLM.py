import logging
from datetime import UTC, datetime
from uuid import uuid5

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.llm.models import MarketPromptContext, ModelSnapshot
from backend.llm.models.LLMRegistry import LLMRegistry
from backend.supabase import LLMConfig, LLMPrediction
from backend.supabase import LLMProvider as LLMProviderEnum
from backend.supabase.consts import (
    LLM_CONFIG_ID_PREFIX,
    LLM_PREDICTION_ID_PREFIX,
    UUID_NAMESPACE,
)
from backend.supabase.queries import (
    get_market,
    get_market_outcomes,
    insert_llm_predictions,
    upsert_llm_configs,
)
from settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PredictorLLM:
    """A single LLM configuration bound to its provider, ready to predict markets.

    One instance per ``llm_config`` row. Construction resolves the provider class
    once; ``predict`` runs a full single-call/single-row cycle against the DB.
    Class-level helpers cover canonical-config bootstrap (``canonical_configs``,
    ``seed_canonical_configs``) so all LLM-side orchestration lives in one place.
    """

    def __init__(self, config: LLMConfig) -> None:
        self.config = config
        self.provider = LLMRegistry[config.provider]

    @classmethod
    def canonical_configs(cls) -> list[LLMConfig]:
        """The set of ``llm_config`` rows the project considers canonical.

        Returned as fully-constructed ORM instances; ``seed_canonical_configs``
        upserts them by id. Add a row here to introduce a new model/experiment.
        """
        return [
            LLMConfig(
                id=f"{LLM_CONFIG_ID_PREFIX}"
                f"{uuid5(UUID_NAMESPACE, 'llm_config:gpt-5-nano-websearch-minimal')}",
                name="gpt-5-nano-minimal-websearch",
                provider=LLMProviderEnum.OPENAI,
                model=ModelSnapshot.GPT_5_NANO_2025_08_07.model,
                model_snapshot=ModelSnapshot.GPT_5_NANO_2025_08_07,
                temperature=None,
                top_p=None,
                max_tokens=None,
                tools=[{"type": "web_search"}],
                extra={"reasoning": {"effort": "minimal"}},
                active=True,
            ),
        ]

    @classmethod
    def seed_canonical_configs(cls) -> bool:
        """Idempotent upsert of every config returned by ``canonical_configs``."""
        try:
            engine = create_engine(settings.database_url)
            configs = cls.canonical_configs()

            with Session(engine) as session:
                response = upsert_llm_configs(session, configs)
                session.commit()

            logger.info(
                f"PredictorLLM.seed_canonical_configs - upserted {response.count} configs"
            )
            return True
        except Exception:
            logger.exception("PredictorLLM.seed_canonical_configs - failed")
            return False

    def predict(self, market_id: str, session: Session) -> bool:
        """Run a single LLM prediction call against ``market_id``.

        On success, inserts one ``llm_prediction`` row pointing at the outcome
        the model picked and returns True. On any failure (missing market,
        provider exception, model returning a label outside the outcome set)
        logs the reason and returns False without writing a row.
        """
        market = get_market(session, market_id).market

        if market is None:
            logger.error(f"PredictorLLM.predict - market {market_id} not found")
            return False

        outcomes = get_market_outcomes(session, market_id).outcomes

        if not outcomes:
            logger.error(f"PredictorLLM.predict - market {market_id} has no outcomes")
            return False

        now = datetime.now(UTC)
        context = MarketPromptContext(
            question=market.question,
            description=market.description,
            end_date=market.end_date,
            outcome_labels=[o.label for o in outcomes],
            today=now.date(),
        )

        try:
            result = self.provider.predict(context, self.config)
        except Exception:
            logger.exception(
                f"PredictorLLM.predict - provider call failed for market={market_id} config={self.config.name}"  # noqa: E501
            )
            return False

        outcome_id_by_label = {o.label: o.id for o in outcomes}
        chosen_outcome_id = outcome_id_by_label.get(result.result)

        if chosen_outcome_id is None:
            logger.error(
                f"PredictorLLM.predict - model returned unknown label {result.result!r} for market={market_id} (known: {list(outcome_id_by_label)})"  # noqa: E501
            )
            return False

        insert_llm_predictions(
            session,
            [
                LLMPrediction(
                    id=f"{LLM_PREDICTION_ID_PREFIX}{
                        uuid5(
                            UUID_NAMESPACE,
                            f'{self.config.id}:{market_id}:{now.isoformat()}',
                        )
                    }",
                    market_id=market_id,
                    outcome_id=chosen_outcome_id,
                    llm_config_id=self.config.id,
                    captured_at=now,
                    tool_calls=result.tool_calls,
                    raw_response=result.raw_response,
                    input_tokens=result.input_tokens,
                    output_tokens=result.output_tokens,
                    latency_ms=result.latency_ms,
                )
            ],
        )
        session.commit()

        return True


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s"
    )
    sys.exit(0 if PredictorLLM.seed_canonical_configs() else 1)
