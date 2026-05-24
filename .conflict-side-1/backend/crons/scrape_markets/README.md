# scrape_markets

Cron job that scrapes active prediction markets from supported sources and upserts them into the database.

## What it does

`main()` runs every scraper in `SCRAPERS` and returns `True` only if all of them succeed. Each scraper fetches the current snapshot of active markets from its source and upserts:

- `Market` — one row per market (question, description, end date, raw payload).
- `Outcome` — one row per tradable outcome (token) within a market.
- `MarketDaily` — one row per outcome per day, capturing price, status flags, and timestamp of capture.

Writes are idempotent via `ON CONFLICT DO UPDATE`, so re-running on the same day overwrites that day's snapshot.

## Sources

| Scraper | Source | Helper | In `SCRAPERS` |
| --- | --- | --- | --- |
| `scrape_polymarket` | Polymarket | [helpers/scrape_polymarket.py](helpers/scrape_polymarket.py) | yes |
| `scrape_kalshi` | Kalshi (unauthenticated public market data endpoint) | [helpers/scrape_kalshi.py](helpers/scrape_kalshi.py) | no — helper exists but is not wired into `main` |

To add a new source, write a `helpers/scrape_<source>.py` exposing a `() -> bool` callable, re-export it from [helpers/__init__.py](helpers/__init__.py), and append it to `SCRAPERS` in [main.py](main.py).

## Running locally

Set the following env vars (a `.env` file at the repo root works — it's loaded via `python-dotenv` in [backend/supabase/consts/database_url.py](../../supabase/consts/database_url.py)):

| Var | Description |
| --- | --- |
| `DB_USER` | Postgres user (e.g. `postgres.<project-ref>` for the Session pooler) |
| `DB_PASSWORD` | Postgres password |
| `DB_HOST` | Postgres host (e.g. `aws-1-<region>.pooler.supabase.com`) |
| `DB_PORT` | Postgres port (e.g. `5432`) |
| `DB_NAME` | Database name (e.g. `postgres`) |
| `DB_SSLMODE` | Optional, defaults to `require`. Set to `disable` when pointing at a local Supabase (`supabase start`) that doesn't speak SSL. |
| `OPENAI_API_KEY` | Required at import time: `helpers/__init__.py` loads `scrape_kalshi.py`, which constructs `Settings()` eagerly. Any non-empty value works if you only run the Polymarket scraper. |

Kalshi market data uses Kalshi's public, unauthenticated endpoints — no API keys are needed.

Run every source:

```bash
uv run python -c "from backend.crons.scrape_markets import main; raise SystemExit(0 if main() else 1)"
```

Run a single source:

```bash
uv run python -c "from backend.crons.scrape_markets.helpers import scrape_polymarket; raise SystemExit(0 if scrape_polymarket() else 1)"
uv run python -c "from backend.crons.scrape_markets.helpers import scrape_kalshi; raise SystemExit(0 if scrape_kalshi() else 1)"
```

## Schedule

Triggered by the GitHub Actions workflow [predict_markets.yml](../../../.github/workflows/predict_markets.yml), which runs every 4 hours on the hour (`0 */4 * * *` UTC, 6×/day). The same workflow then runs the [predict_markets](../predict_markets/README.md) cron as a dependent job.

In CI only `scrape_polymarket` is called — not `main()` — so adding a scraper to `SCRAPERS` does **not** make CI pick it up. The workflow must be edited to invoke the new scraper (today, as its own job).

`workflow_dispatch` exposes a `polymarket` boolean input (defaults to `true`); untick it to skip the scrape on a manual run. The scheduled cron always runs it.

Secrets come from the GitHub Environment selected by the workflow (`prd` by default, `stg` available via manual dispatch): `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`, `OPENAI_API_KEY`.
