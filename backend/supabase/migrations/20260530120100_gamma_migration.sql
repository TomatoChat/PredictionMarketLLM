-- Migrate the scrape source from the CLOB API to Polymarket's gamma-api.
--
-- Consequences for the schema:
--   * gamma exposes per-market volume/liquidity (CLOB did not) -> fold them into
--     the price time-series, which is renamed outcome_snapshot ->
--     market_outcome_snapshot.
--   * market_daily is dropped: at daily cadence it duplicated outcome_snapshot,
--     its status flags become constant under active-only snapshotting, and
--     resolution now lives in outcome.market_winner.
--   * market status (active/closed/archived) moves onto the market dimension,
--     since market_daily was its only previous home and get_active_market_ids
--     needs it.

-- 1. Market gets current-status columns.
alter table public.market
    add column active boolean not null default false,
    add column closed boolean not null default false,
    add column archived boolean not null default false;

comment on column public.market.active is
    'Current status: whether the market is active (not deleted/disabled) at last scrape.';
comment on column public.market.closed is
    'Current status: whether the market has closed (resolved / no longer trading) at last scrape.';
comment on column public.market.archived is
    'Current status: whether the market is archived (hidden from default listings) at last scrape.';

-- 2. Drop market_daily (superseded by market_outcome_snapshot + market status).
drop table if exists public.market_daily;

-- 3. Rename outcome_snapshot -> market_outcome_snapshot and add volume/liquidity.
alter table public.outcome_snapshot rename to market_outcome_snapshot;
alter index ix_outcome_snapshot_outcome_captured
    rename to ix_market_outcome_snapshot_outcome_captured;

alter table public.market_outcome_snapshot
    add column volume numeric(20, 6),
    add column liquidity numeric(20, 6);

comment on column public.market_outcome_snapshot.volume is
    'Market-level cumulative volume reported by the source; duplicated across the market''s outcome rows.';
comment on column public.market_outcome_snapshot.liquidity is
    'Market-level liquidity reported by the source; duplicated across the market''s outcome rows.';
