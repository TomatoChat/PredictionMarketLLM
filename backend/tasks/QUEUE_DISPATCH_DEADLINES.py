"""Single source of truth for per-queue Cloud Tasks dispatch deadlines (seconds).

A queue's dispatch deadline is how long Cloud Tasks waits for the worker to
respond before treating the attempt as failed and retrying. ``enqueue`` applies
the value for the target queue automatically, so every task on a queue gets the
same deadline and call sites never hardcode it.

INVARIANT: each deadline MUST be <= the target Cloud Run service's ``timeout``
in that service's deployment.yaml, or Cloud Run kills the request before the
deadline fires. Keep these in lockstep:

    queue                       -> service     deployment.yaml timeout
    scrape-markets-polymarket   -> polymarket  180
    save-embeddings-markets     -> llm         180  (= max(embed 60, predict 180))
    solve-market-llm            -> llm         180

Values are right-sized from measured per-task local runtimes (scrape page <=5s,
embed ~1s, predict ~2-9s) plus generous margin for cold starts and slow
web_search runs. Cloud Tasks allows 15..1800s; its own default (used for any
queue absent from this map) is 600s.
"""

QUEUE_DISPATCH_DEADLINES: dict[str, int] = {
    "scrape-markets-polymarket": 180,
    "save-embeddings-markets": 60,
    "solve-market-llm": 180,
}
