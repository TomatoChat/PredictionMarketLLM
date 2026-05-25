create table outcome_snapshot (
    outcome_id text not null references outcome(id) on delete cascade,
    captured_at timestamptz not null default now(),
    price numeric(10, 6),
    primary key (outcome_id, captured_at)
);

create index ix_outcome_snapshot_outcome_captured
    on outcome_snapshot (outcome_id, captured_at);
