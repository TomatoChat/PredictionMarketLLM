create type llm_provider as enum ('openai', 'anthropic', 'google');

create table llm_config (
    id text primary key,
    name text not null unique,
    provider llm_provider not null,
    model text not null,
    model_snapshot text,
    temperature numeric(3, 2),
    top_p numeric(3, 2),
    max_tokens integer,
    tools jsonb not null default '[]',
    extra jsonb not null default '{}',
    active boolean not null default true,
    created_at timestamptz not null default now()
);

create index ix_llm_config_provider_active on llm_config (provider, active);

create table llm_prediction (
    id text primary key,
    market_id text not null references market (id) on delete cascade,
    outcome_id text references outcome (id) on delete cascade,
    llm_config_id text not null references llm_config (id) on delete cascade,
    captured_at timestamptz not null default now(),
    tool_calls jsonb,
    raw_response jsonb not null,
    input_tokens integer,
    output_tokens integer,
    latency_ms integer
);

create index ix_llm_prediction_market_captured on llm_prediction (market_id, captured_at desc);
create index ix_llm_prediction_outcome_captured on llm_prediction (outcome_id, captured_at desc);
create index ix_llm_prediction_config_captured on llm_prediction (llm_config_id, captured_at desc);

comment on type llm_provider is 'LLM provider whose SDK is used to generate the prediction.';

comment on column llm_config.id is 'Prefixed identifier ''cfg_<uuid v5>'' derived from name; stable across re-inserts.';
comment on column llm_config.name is 'Human-readable label for this experiment configuration (e.g. ''gpt-5-nano-websearch-minimal'').';
comment on column llm_config.provider is 'Which provider SDK to call.';
comment on column llm_config.model is 'Provider-specific model family/alias (e.g. ''gpt-5-nano'', ''claude-sonnet-4-6'').';
comment on column llm_config.model_snapshot is 'Pinned provider-specific model snapshot (e.g. ''gpt-5-nano-2025-08-07''); null leaves the provider to resolve from ``model``.';
comment on column llm_config.temperature is 'Sampling temperature passed to the provider; null leaves the provider default.';
comment on column llm_config.top_p is 'Nucleus sampling top_p passed to the provider; null leaves the provider default.';
comment on column llm_config.max_tokens is 'Maximum tokens to generate; null leaves the provider default.';
comment on column llm_config.tools is 'Array of tool specs the model is allowed to call (e.g. [{"type":"web_search"},{"type":"exa"}]).';
comment on column llm_config.extra is 'Object of provider-specific knobs that don''t have a dedicated column (e.g. reasoning_effort, thinking budget, seed).';
comment on column llm_config.active is 'Whether to include this config in scheduled prediction runs.';
comment on column llm_config.created_at is 'Wall-clock timestamp when this config row was inserted.';

comment on column llm_prediction.id is 'Prefixed identifier ''pred_<uuid v5>''; one row per LLM call against a market.';
comment on column llm_prediction.market_id is 'Market the prediction is about (prefixed ''mkt_<uuid>'').';
comment on column llm_prediction.outcome_id is 'Outcome the model picked as the predicted winning resolution (prefixed ''out_<uuid>''); null when the call failed.';
comment on column llm_prediction.llm_config_id is 'Config used to generate this prediction (prefixed ''cfg_<uuid>'').';
comment on column llm_prediction.captured_at is 'Wall-clock timestamp when the prediction call completed.';
comment on column llm_prediction.tool_calls is 'Tool invocations made during the run (tool name, arguments, results).';
comment on column llm_prediction.raw_response is 'Full raw provider response, kept as an escape hatch for fields not yet normalized.';
comment on column llm_prediction.input_tokens is 'Input/prompt token count reported by the provider.';
comment on column llm_prediction.output_tokens is 'Output/completion token count reported by the provider.';
comment on column llm_prediction.latency_ms is 'End-to-end latency of the provider call in milliseconds.';
