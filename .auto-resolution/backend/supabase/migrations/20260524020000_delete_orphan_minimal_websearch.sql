-- Delete the orphaned `gpt-5-nano-minimal-websearch` llm_config row.
--
-- The config was renamed to `gpt-5-low-websearch` in PR #20, which changes the
-- deterministic id (cfg_<uuid5(name)>). The old row stayed in the DB with
-- active = true and kept running in the scheduled cron, where OpenAI rejects
-- every call because `reasoning.effort = 'minimal'` is incompatible with the
-- `web_search` tool. Delete the orphan; llm_prediction rows pointing at it
-- cascade-delete with it (see schema.py: ondelete="CASCADE").

delete from public.llm_config
    where id = 'cfg_1d2db81d-9f13-58d1-a176-4dcda1bd67b2'
      and name = 'gpt-5-nano-minimal-websearch';
