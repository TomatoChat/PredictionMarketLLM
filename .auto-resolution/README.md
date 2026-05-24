# PredictionMarketLLM

[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![ty](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ty/main/assets/badge/v0.json)](https://github.com/astral-sh/ty)

Let LLMs play on prediction markets.

## Requirements

- Python `>=3.14`
- [uv](https://docs.astral.sh/uv/)

## Setup

```bash
uv sync
uv run pre-commit install
```

## Crons

| Cron | Description |
| --- | --- |
| [scrape_markets](backend/crons/scrape_markets/README.md) | Scrapes active prediction markets and upserts daily snapshots. |
| [predict_markets](backend/crons/predict_markets/README.md) | Runs every active `llm_config` against every active market and stores the predictions. |

Both run from the [predict_markets.yml](.github/workflows/predict_markets.yml) GitHub Actions workflow, every 4 hours starting at midnight UTC (6×/day). The `predict` job depends on `polymarket` completing first.
