# predict_markets

Cron job that runs LLM predictions against active prediction markets and appends one `llm_prediction` row per (market × config) call.

## What it does

The entrypoint is [main.py](main.py); `python -m backend.crons.predict_markets` runs it. Two modes:

| CLI | Behavior |
| --- | --- |
| _(no args)_ | Calls `predict_all_configs()` — looks up every `llm_config` with `active = true` and runs each one against every active market. |
| `--config <name>` | Calls `predict_with_config(name)` — runs that one config against every active market. Inactive configs are skipped (returns `True`). |
| `--config <name> --market-id <mkt_…>` | Runs that one config against a single market. The `active` flag is ignored in this mode. |

`--market-id` requires `--config`. Exit code is `0` on success, `1` on failure.

For each (config × market) call, [PredictorLLM](../../llm/classes/PredictorLLM.py) builds the prompt, invokes the configured provider/model, and writes one `LLMPrediction` row — `outcome_id` is the outcome the model picked, plus the full raw response.

A run is considered successful only if every market succeeds (`n_failed == 0`).

## Configs

Configs live in the `llm_config` table — one row per experiment ([`backend/supabase/schema.py:205`](../../supabase/schema.py:205)). Each row pins a provider, model (+ optional snapshot), sampling knobs, tools, and an `active` flag. `predict_all_configs` only iterates configs where `active = true`; toggle a row off to take it out of the cron without deleting it.

Configs are seeded via [`upsert_llm_configs`](../../supabase/queries/upsert_llm_configs.py) — the `id` is a deterministic `cfg_<uuid v5>` derived from `name`, so re-running the seed updates in place.

## Running locally

Set the same DB vars as the [scrape_markets](../scrape_markets/README.md) cron, plus a provider key for whichever providers your active configs use:

| Var | Description |
| --- | --- |
| `DB_USER` / `DB_PASSWORD` / `DB_HOST` / `DB_PORT` / `DB_NAME` | Postgres connection — see [scrape_markets](../scrape_markets/README.md#running-locally). |
| `DB_SSLMODE` | Optional, defaults to `require`. Set to `disable` for local Supabase. |
| `OPENAI_API_KEY` | Required (loaded at import time via `Settings()`). Used by any config with `provider = openai`. |

Predict for every active config:

```bash
uv run python -m backend.crons.predict_markets
```

One config, all active markets:

```bash
uv run python -m backend.crons.predict_markets --config gpt-4.1-temp0
```

One config, one market:

```bash
uv run python -m backend.crons.predict_markets --config gpt-4.1-temp0 --market-id mkt_1234abcd
```

## Schedule

Triggered by the GitHub Actions workflow [predict_markets.yml](../../../.github/workflows/predict_markets.yml), every 4 hours on the hour (`0 */4 * * *` UTC, 6×/day). The `predict` job depends on the `polymarket` scrape job (`needs: [polymarket]`) and runs as long as the scrape isn't cancelled — it still runs if scraping failed (`!cancelled()`).

`workflow_dispatch` exposes a `predict` boolean input (defaults to `true`); untick it to skip on a manual run. The scheduled cron always runs it.

Secrets come from the GitHub Environment selected by the workflow (`prd` by default, `stg` via manual dispatch): `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `OPENAI_API_KEY`.
