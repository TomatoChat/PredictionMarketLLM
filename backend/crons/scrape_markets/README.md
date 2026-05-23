# scrape_markets

Cron job that scrapes active prediction markets from supported sources and upserts them into the database.

## What it does

`main()` runs every scraper in `SCRAPERS` and returns `True` only if all of them succeed. Each scraper fetches the current snapshot of active markets from its source and upserts:

- `Market` — one row per market (question, description, end date, raw payload).
- `Outcome` — one row per tradable outcome (token) within a market.
- `MarketDaily` — one row per outcome per day, capturing price, status flags, and timestamp of capture.

Writes are idempotent via `ON CONFLICT DO UPDATE`, so re-running on the same day overwrites that day's snapshot.

## Sources

| Scraper | Source | Helper |
| --- | --- | --- |
| `scrape_polymarket` | Polymarket | [helpers/scrape_polymarket.py](helpers/scrape_polymarket.py) |

To add a new source, write a `helpers/scrape_<source>.py` exposing a `() -> bool` callable, re-export it from [helpers/__init__.py](helpers/__init__.py), and append it to `SCRAPERS` in [main.py](main.py).

## Running locally

Set the following env vars (a `.env` file at the repo root works — it's loaded via `python-dotenv` in [backend/supabase/consts/database_url.py](../../supabase/consts/database_url.py)):

| Var | Description |
| --- | --- |
| `user` | Postgres user (e.g. `postgres`) |
| `password` | Postgres password |
| `host` | Postgres host (e.g. `db.<project-ref>.supabase.co`) |
| `port` | Postgres port (e.g. `5432`) |
| `dbname` | Database name (e.g. `postgres`) |

Then:

```bash
uv run python -c "from backend.crons.scrape_markets import main; raise SystemExit(0 if main() else 1)"
```

## Schedule

Triggered by the GitHub Actions workflow [scrape_markets.yml](../../../.github/workflows/scrape_markets.yml), which runs 6 times a day every 4 hours starting at midnight New York time (00, 04, 08, 12, 16, 20 NY). The DB connection vars are provided as the repository secrets `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`.
