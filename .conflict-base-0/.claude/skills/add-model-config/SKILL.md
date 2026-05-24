---
name: add-model-config
description: Use this skill whenever the user asks to add, register, seed, or experiment with a new LLM configuration in this repo — i.e. a new combination of provider, model, sampling params (temperature, top_p, max_tokens), tools (web_search, etc.), and provider-specific extras (reasoning effort, seed, …). Triggers on phrases like "add a new model config", "add a config for <model>", "seed a new llm_config", "add a new experiment", "register <provider>/<model>", or when the user describes a model + a tool/effort combo they want available to the predict cron. Do NOT trigger for renaming an existing config (use a different workflow that deactivates the old row) or for prompting changes that don't touch the config table.
---

# Add a new model config

A "config" here = one row in the `llm_config` table, declared in [`PredictorLLM.canonical_configs()`](../../../backend/llm/classes/PredictorLLM.py). Each config is a fully specified provider call (model + sampling + tools + extras), and the `predict_markets` cron runs every `active = true` config against every active market.

## Steps

1. **Pick a name.** Convention: `<model>-<knob>-<tools>` lowercase with hyphens (e.g. `gpt-5-low-websearch`, `gpt-5-nano-medium`, `claude-sonnet-4-6-temp0`). The name is human-facing and used as the CLI argument `--config <name>`. It also derives the row id via `uuid5(UUID_NAMESPACE, 'llm_config:<unique-string>')` — see step 3.

2. **Confirm the model is in the snapshot enum.** Check `backend/llm/models/ModelSnapshot.py` (re-exported from `backend.llm.models`). If the snapshot you want isn't listed, add it there first — `model_snapshot` is what gets sent to the provider; `model` is the family alias.

3. **Add an entry to `canonical_configs()`** in [`backend/llm/classes/PredictorLLM.py`](../../../backend/llm/classes/PredictorLLM.py). Pattern:

   ```python
   LLMConfig(
       id=f"{LLM_CONFIG_ID_PREFIX}"
       f"{uuid5(UUID_NAMESPACE, 'llm_config:<unique-stable-string>')}",
       name="<same-as-CLI>",
       provider=LLMProviderEnum.OPENAI,  # or ANTHROPIC / GOOGLE
       model=ModelSnapshot.<ENUM>.model,
       model_snapshot=ModelSnapshot.<ENUM>,
       temperature=None,        # or Decimal("0.0")
       top_p=None,
       max_tokens=None,
       tools=[{"type": "web_search"}],  # or [] / provider-specific shape
       extra={"reasoning": {"effort": "low"}},  # provider-specific knobs
       active=True,
   ),
   ```

   The `'llm_config:<unique-stable-string>'` argument to `uuid5` is the id seed — it must be unique per row and stable (changing it later orphans the old row in the DB).

4. **Validate provider constraints before seeding.** Common traps:
   - **OpenAI `gpt-5*` + `web_search` is incompatible with `reasoning.effort = "minimal"`.** Use `"low"` or higher when web_search is in `tools`.
   - **Temperature/top_p are ignored by reasoning models** — leave them `None` to avoid confusion.
   - **`max_tokens`** maps to `max_output_tokens` for the Responses API; null = provider default.
   - **`tools` shape is verbatim what the provider wants** — e.g. OpenAI uses `[{"type": "web_search"}]`; this is not abstracted.

5. **Seed it into whichever DB `.env` points at.**

   ```bash
   uv run python -m backend.llm.classes.PredictorLLM
   ```

   Idempotent — re-runs upsert by id. Confirm the row landed:

   ```bash
   uv run python -c "
   from sqlalchemy import create_engine, text
   from sqlalchemy.orm import Session
   from settings import get_settings
   with Session(create_engine(get_settings().database_url)) as s:
       rows = s.execute(text(\"SELECT name, provider, model, model_snapshot, tools, extra, active FROM llm_config ORDER BY created_at DESC LIMIT 5\")).all()
       for r in rows: print(r)
   "
   ```

6. **Dry-run the new config against one market** before merging or before letting it run in CI.

   ```bash
   # grab one active market id
   uv run python -c "
   from sqlalchemy import create_engine
   from sqlalchemy.orm import Session
   from backend.supabase.queries import get_active_market_ids
   from settings import get_settings
   with Session(create_engine(get_settings().database_url)) as s:
       print(get_active_market_ids(s).market_ids[:3])
   "

   # dry-run (calls the provider, no DB write)
   uv run python -m backend.crons.predict_markets \
     --config <new-name> \
     --market-id mkt_<paste> \
     --dry-run
   ```

   You should see an `INFO ... DRY RUN ...` line with the chosen outcome label and token counts. If the provider rejects the combination (e.g. tool/effort mismatch), fix the config and re-seed before going further.

7. **Run for real against the local DB** to make sure the insert path works:

   ```bash
   uv run python -m backend.crons.predict_markets --config <new-name> --market-id mkt_<id>
   ```

   Then check the row landed in `llm_prediction`.

8. **Decide on `active`.** If the new config is exploratory and shouldn't run in the scheduled prd cron yet, set `active=False` in `canonical_configs()` until you're ready. Toggling later requires a re-seed.

## Don'ts

- **Don't insert directly into `llm_config`** with ad-hoc SQL — `canonical_configs()` is the source of truth; any row not in there is orphaned and will confuse future maintainers.
- **Don't rename an existing config to "fix" it.** Rename = new id = old row stays in the DB. If you must rename, also flip the old row to `active = false` (or delete, accepting the cascade onto `llm_prediction`).
- **Don't reuse the same `uuid5` seed string for a different config.** The id collision will silently overwrite the existing row on next seed.

## Reference

- [`PredictorLLM.canonical_configs`](../../../backend/llm/classes/PredictorLLM.py) — where the configs live.
- [`backend/supabase/schema.py:205`](../../../backend/supabase/schema.py) — the `LLMConfig` ORM model with column comments explaining every field.
- [`backend/crons/predict_markets/README.md`](../../../backend/crons/predict_markets/README.md) — how the cron consumes configs.
