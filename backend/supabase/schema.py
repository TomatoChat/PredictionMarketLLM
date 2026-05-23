from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for every ORM model in the project."""

    def model_dump(self) -> dict[str, Any]:
        """Return a {column_name: value} dict, mirroring the Pydantic `model_dump` API.

        Suitable for passing into `insert(Table).values([...])`. Columns not yet
        assigned on the instance fall back to None.
        """
        return {c.key: getattr(self, c.key, None) for c in self.__table__.columns}


class Source(StrEnum):
    """Prediction-market data source. The string value matches the Postgres enum label."""

    POLYMARKET = "polymarket"
    KALSHI = "kalshi"


class Market(Base):
    """One row per market across all sources. Slow-changing dimension; id is `mkt_<uuid v5>` derived from (source, source_market_id)."""

    __tablename__ = "market"
    __table_args__ = (
        UniqueConstraint("source", "source_market_id", name="uq_market_source"),
        Index("ix_market_source_last_seen", "source", "last_seen_at"),
    )

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        comment="Prefixed identifier 'mkt_<uuid v5>' derived from (source, source_market_id); stable across re-scrapes.",
    )
    source: Mapped[Source] = mapped_column(
        SqlEnum(
            Source,
            name="source",
            native_enum=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        comment="Which prediction market this row came from.",
    )
    source_market_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="External market id at the source (Polymarket condition_id, Kalshi ticker, ...).",
    )
    question: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable question that this market resolves.",
    )
    description: Mapped[str | None] = mapped_column(
        Text, comment="Long-form market description, including resolution criteria."
    )
    slug: Mapped[str | None] = mapped_column(
        Text, comment="URL-safe slug used on the source's website."
    )
    end_date: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), comment="Scheduled resolution deadline of the market."
    )
    raw: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full raw payload from the source API, kept as an escape hatch for fields not yet normalized.",
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp of the first scrape that recorded this market.",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp of the most recent scrape that recorded this market.",
    )


class Outcome(Base):
    """One row per tradable outcome of a market. Binary markets have two rows (Yes/No); Polymarket neg-risk markets can have more."""

    __tablename__ = "outcome"
    __table_args__ = (
        UniqueConstraint("market_id", "source_outcome_id", name="uq_outcome_market"),
        Index("ix_outcome_market_id", "market_id"),
    )

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        comment="Prefixed identifier 'out_<uuid v5>' derived from (market.id, source_outcome_id); stable across re-scrapes.",
    )
    market_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("market.id", ondelete="CASCADE"),
        nullable=False,
        comment="Market this outcome belongs to (prefixed 'mkt_<uuid>').",
    )
    source_outcome_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="External outcome id at the source (Polymarket token_id, Kalshi 'yes'/'no', ...).",
    )
    label: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Human-readable outcome label ('Yes', 'No', team name, ...).",
    )
    resolved_winner: Mapped[bool | None] = mapped_column(
        Boolean,
        comment="True if this outcome won at resolution; null while unresolved.",
    )


class MarketDaily(Base):
    """Daily snapshot of an outcome's price plus market-level volume/status. Append-only time-series, PK (outcome_id, snapshot_date)."""

    __tablename__ = "market_daily"

    outcome_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("outcome.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Outcome being snapshotted (prefixed 'out_<uuid>').",
    )
    snapshot_date: Mapped[date] = mapped_column(
        Date,
        primary_key=True,
        comment="Logical date of the snapshot (one row per outcome per day).",
    )
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Wall-clock timestamp when the scrape that produced this row ran.",
    )
    price: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 6),
        comment="Implied probability for this outcome between 0 and 1 (last traded price).",
    )
    volume: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        comment="Market-level cumulative volume reported by the source; duplicated across the market's outcome rows.",
    )
    liquidity: Mapped[Decimal | None] = mapped_column(
        Numeric(20, 6),
        comment="Market-level liquidity reported by the source; duplicated across the market's outcome rows.",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the market was active at the time of the snapshot.",
    )
    closed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the market was closed at the time of the snapshot.",
    )
    archived: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the market was archived at the time of the snapshot.",
    )
    accepting_orders: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="Whether the order book was accepting orders at the time of the snapshot.",
    )


class LLMProvider(StrEnum):
    """LLM provider whose SDK is used to generate the prediction. The string value matches the Postgres enum label."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"


class LLMConfig(Base):
    """One row per experiment configuration. id is `cfg_<uuid v5>` derived from name; tools and extra are jsonb escape hatches."""

    __tablename__ = "llm_config"
    __table_args__ = (Index("ix_llm_config_provider_active", "provider", "active"),)

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        comment="Prefixed identifier 'cfg_<uuid v5>' derived from name; stable across re-inserts.",
    )
    name: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="Human-readable label for this experiment configuration (e.g. 'gpt-4.1-temp0-with-exa').",
    )
    provider: Mapped[LLMProvider] = mapped_column(
        SqlEnum(
            LLMProvider,
            name="llm_provider",
            native_enum=True,
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        comment="Which provider SDK to call.",
    )
    model: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Provider-specific model identifier (e.g. 'gpt-4.1', 'claude-sonnet-4-6').",
    )
    temperature: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        comment="Sampling temperature passed to the provider; null leaves the provider default.",
    )
    top_p: Mapped[Decimal | None] = mapped_column(
        Numeric(3, 2),
        comment="Nucleus sampling top_p passed to the provider; null leaves the provider default.",
    )
    max_tokens: Mapped[int | None] = mapped_column(
        Integer,
        comment="Maximum tokens to generate; null leaves the provider default.",
    )
    tools: Mapped[list] = mapped_column(
        JSONB,
        nullable=False,
        server_default="[]",
        comment='Array of tool specs the model is allowed to call (e.g. [{"type":"web_search"},{"type":"exa"}]).',
    )
    extra: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Object of provider-specific knobs that don't have a dedicated column (e.g. reasoning_effort, thinking budget, seed).",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default="true",
        comment="Whether to include this config in scheduled prediction runs.",
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Wall-clock timestamp when this config row was inserted.",
    )


class LLMPrediction(Base):
    """One row per LLM call against a market. Append-only; ``outcome_id`` points to the outcome the model picked as the winner."""

    __tablename__ = "llm_prediction"
    __table_args__ = (
        Index("ix_llm_prediction_market_captured", "market_id", "captured_at"),
        Index("ix_llm_prediction_outcome_captured", "outcome_id", "captured_at"),
        Index("ix_llm_prediction_config_captured", "llm_config_id", "captured_at"),
    )

    id: Mapped[str] = mapped_column(
        Text,
        primary_key=True,
        comment="Prefixed identifier 'pred_<uuid v5>'; one row per LLM call against a market.",
    )
    market_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("market.id", ondelete="CASCADE"),
        nullable=False,
        comment="Market the prediction is about (prefixed 'mkt_<uuid>').",
    )
    outcome_id: Mapped[str | None] = mapped_column(
        Text,
        ForeignKey("outcome.id", ondelete="CASCADE"),
        comment="Outcome the model picked as the predicted winning resolution (prefixed 'out_<uuid>'); null when the call failed.",
    )
    llm_config_id: Mapped[str] = mapped_column(
        Text,
        ForeignKey("llm_config.id", ondelete="CASCADE"),
        nullable=False,
        comment="Config used to generate this prediction (prefixed 'cfg_<uuid>').",
    )
    captured_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Wall-clock timestamp when the prediction call completed.",
    )
    model_snapshot: Mapped[str | None] = mapped_column(
        Text,
        comment="Resolved provider-specific model snapshot/version that actually answered (e.g. 'gpt-5-nano-2025-08-07'); may differ from llm_config.model when an alias was used.",
    )
    tool_calls: Mapped[list | None] = mapped_column(
        JSONB,
        comment="Tool invocations made during the run (tool name, arguments, results).",
    )
    raw_response: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Full raw provider response, kept as an escape hatch for fields not yet normalized.",
    )
    input_tokens: Mapped[int | None] = mapped_column(
        Integer, comment="Input/prompt token count reported by the provider."
    )
    output_tokens: Mapped[int | None] = mapped_column(
        Integer, comment="Output/completion token count reported by the provider."
    )
    latency_ms: Mapped[int | None] = mapped_column(
        Integer, comment="End-to-end latency of the provider call in milliseconds."
    )
    error: Mapped[str | None] = mapped_column(
        Text, comment="Error message if the call failed; null on success."
    )
