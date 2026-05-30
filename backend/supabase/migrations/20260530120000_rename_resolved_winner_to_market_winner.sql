-- Rename outcome.resolved_winner -> outcome.market_winner.
--
-- The column marks, per outcome, whether it won at market resolution. It is the
-- canonical resolution signal (resolution is derived from market_winner IS NOT
-- NULL); market_daily/outcome_snapshot only carry price history for active
-- markets and cannot answer "who won". Renamed for clarity now that the scraper
-- ingests all markets (not just active ones) and populates it on close.

alter table public.outcome rename column resolved_winner to market_winner;

comment on column public.outcome.market_winner is
    'True if this outcome won at market resolution; null while unresolved.';
