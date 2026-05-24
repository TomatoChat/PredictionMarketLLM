create type source as enum ('polymarket', 'kalshi');

create table market (
    id text primary key,
    source source not null,
    source_market_id text not null,
    question text not null,
    description text,
    slug text,
    end_date timestamptz,
    raw jsonb not null,
    first_seen_at timestamptz not null default now(),
    last_seen_at timestamptz not null default now(),
    constraint uq_market_source unique (source, source_market_id)
);

create index ix_market_source_last_seen on market (source, last_seen_at desc);

create table outcome (
    id text primary key,
    market_id text not null references market (id) on delete cascade,
    source_outcome_id text not null,
    label text not null,
    resolved_winner boolean,
    constraint uq_outcome_market unique (market_id, source_outcome_id)
);

create index ix_outcome_market_id on outcome (market_id);

create table market_daily (
    outcome_id text not null references outcome (id) on delete cascade,
    snapshot_date date not null,
    captured_at timestamptz not null default now(),
    price numeric(10, 6),
    volume numeric(20, 6),
    liquidity numeric(20, 6),
    active boolean not null,
    closed boolean not null,
    archived boolean not null,
    accepting_orders boolean not null,
    primary key (outcome_id, snapshot_date)
);

comment on column market.id is 'Prefixed identifier ''mkt_<uuid v5>'' derived from (source, source_market_id); stable across re-scrapes.';
comment on column market.source is 'Which prediction market this row came from.';
comment on column market.source_market_id is 'External market id at the source (Polymarket condition_id, Kalshi ticker, ...).';
comment on column market.question is 'Human-readable question that this market resolves.';
comment on column market.description is 'Long-form market description, including resolution criteria.';
comment on column market.slug is 'URL-safe slug used on the source''s website.';
comment on column market.end_date is 'Scheduled resolution deadline of the market.';
comment on column market.raw is 'Full raw payload from the source API, kept as an escape hatch for fields not yet normalized.';
comment on column market.first_seen_at is 'Timestamp of the first scrape that recorded this market.';
comment on column market.last_seen_at is 'Timestamp of the most recent scrape that recorded this market.';

comment on column outcome.id is 'Prefixed identifier ''out_<uuid v5>'' derived from (market.id, source_outcome_id); stable across re-scrapes.';
comment on column outcome.market_id is 'Market this outcome belongs to (prefixed ''mkt_<uuid>'').';
comment on column outcome.source_outcome_id is 'External outcome id at the source (Polymarket token_id, Kalshi ''yes''/''no'', ...).';
comment on column outcome.label is 'Human-readable outcome label (''Yes'', ''No'', team name, ...).';
comment on column outcome.resolved_winner is 'True if this outcome won at resolution; null while unresolved.';

comment on column market_daily.outcome_id is 'Outcome being snapshotted (prefixed ''out_<uuid>'').';
comment on column market_daily.snapshot_date is 'Logical date of the snapshot (one row per outcome per day).';
comment on column market_daily.captured_at is 'Wall-clock timestamp when the scrape that produced this row ran.';
comment on column market_daily.price is 'Implied probability for this outcome between 0 and 1 (last traded price).';
comment on column market_daily.volume is 'Market-level cumulative volume reported by the source; duplicated across the market''s outcome rows.';
comment on column market_daily.liquidity is 'Market-level liquidity reported by the source; duplicated across the market''s outcome rows.';
comment on column market_daily.active is 'Whether the market was active at the time of the snapshot.';
comment on column market_daily.closed is 'Whether the market was closed at the time of the snapshot.';
comment on column market_daily.archived is 'Whether the market was archived at the time of the snapshot.';
comment on column market_daily.accepting_orders is 'Whether the order book was accepting orders at the time of the snapshot.';
