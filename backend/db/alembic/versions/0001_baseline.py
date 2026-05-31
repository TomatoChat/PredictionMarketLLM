"""baseline — schema as of the Supabase→Cloud SQL cutover.

Creates the full schema (5 tables + 2 enums) in one shot, matching
`backend/db/schema.py`. On a fresh DB this is the entrypoint; on the existing
production DB (which already has these tables from the original `supabase db
push` runs) the operator runs `alembic stamp 0001_baseline` once after data
import so this revision is recorded as applied without re-running.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-05-31
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    source_enum = postgresql.ENUM(
        "polymarket", "kalshi", name="source", create_type=False
    )
    llm_provider_enum = postgresql.ENUM(
        "openai",
        "anthropic",
        "google",
        name="llm_provider",
        create_type=False,
    )
    source_enum.create(op.get_bind(), checkfirst=True)
    llm_provider_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "market",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("source", source_enum, nullable=False),
        sa.Column("source_market_id", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("slug", sa.Text(), nullable=True),
        sa.Column("end_date", postgresql.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "closed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "archived",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("raw_path", sa.Text(), nullable=True),
        sa.Column(
            "first_seen_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("source", "source_market_id", name="uq_market_source"),
    )
    op.create_index("ix_market_source_last_seen", "market", ["source", "last_seen_at"])

    op.create_table(
        "outcome",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "market_id",
            sa.Text(),
            sa.ForeignKey("market.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_outcome_id", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("market_winner", sa.Boolean(), nullable=True),
        sa.UniqueConstraint("market_id", "source_outcome_id", name="uq_outcome_market"),
    )
    op.create_index("ix_outcome_market_id", "outcome", ["market_id"])

    op.create_table(
        "market_outcome_snapshot",
        sa.Column(
            "outcome_id",
            sa.Text(),
            sa.ForeignKey("outcome.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "captured_at",
            postgresql.TIMESTAMP(timezone=True),
            primary_key=True,
            server_default=sa.func.now(),
        ),
        sa.Column("price", sa.Numeric(10, 6), nullable=True),
        sa.Column("volume", sa.Numeric(20, 6), nullable=True),
        sa.Column("liquidity", sa.Numeric(20, 6), nullable=True),
    )
    op.create_index(
        "ix_market_outcome_snapshot_outcome_captured",
        "market_outcome_snapshot",
        ["outcome_id", "captured_at"],
    )

    op.create_table(
        "llm_config",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False, unique=True),
        sa.Column("provider", llm_provider_enum, nullable=False),
        sa.Column("model", sa.Text(), nullable=False),
        sa.Column("model_snapshot", sa.Text(), nullable=True),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=True),
        sa.Column("top_p", sa.Numeric(3, 2), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "tools",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "extra",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("true"),
        ),
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_llm_config_provider_active", "llm_config", ["provider", "active"]
    )

    op.create_table(
        "llm_prediction",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column(
            "market_id",
            sa.Text(),
            sa.ForeignKey("market.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "outcome_id",
            sa.Text(),
            sa.ForeignKey("outcome.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "llm_config_id",
            sa.Text(),
            sa.ForeignKey("llm_config.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "captured_at",
            postgresql.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("tool_calls", postgresql.JSONB(), nullable=True),
        sa.Column("raw_response_path", sa.Text(), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
    )
    op.create_index(
        "ix_llm_prediction_market_captured",
        "llm_prediction",
        ["market_id", "captured_at"],
    )
    op.create_index(
        "ix_llm_prediction_outcome_captured",
        "llm_prediction",
        ["outcome_id", "captured_at"],
    )
    op.create_index(
        "ix_llm_prediction_config_captured",
        "llm_prediction",
        ["llm_config_id", "captured_at"],
    )


def downgrade() -> None:
    op.drop_table("llm_prediction")
    op.drop_table("llm_config")
    op.drop_table("market_outcome_snapshot")
    op.drop_table("outcome")
    op.drop_table("market")
    postgresql.ENUM(name="llm_provider").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="source").drop(op.get_bind(), checkfirst=True)
