import gzip
import json
from concurrent.futures import ThreadPoolExecutor
from functools import cached_property
from typing import Any

from google.cloud import storage

from settings import get_settings

UPLOAD_CONCURRENCY = 16


class RawStore:
    """Writes raw JSON payloads to a GCS bucket so they stay out of Postgres.

    ``market.raw`` and ``llm_prediction.raw_response`` are escape-hatch blobs
    that are never queried relationally. Keeping them inline bloats the DB (and
    every read's egress), so they live in GCS as gzip'd JSON and the DB keeps
    only the ``gs://`` path. The client is built lazily so credentials/bucket
    are only resolved when an upload actually runs.
    """

    @cached_property
    def client(self) -> storage.Client:
        return storage.Client()

    @cached_property
    def bucket(self) -> storage.Bucket:
        name = get_settings().GCS_RAW_BUCKET
        if not name:
            raise RuntimeError("GCS_RAW_BUCKET is not configured")
        return self.client.bucket(name)

    def put_json(self, key: str, payload: Any) -> str:
        """Gzip-encode ``payload`` as JSON, upload to ``key``, return the gs:// path."""
        data = gzip.compress(json.dumps(payload, default=str).encode("utf-8"))
        self.bucket.blob(key).upload_from_string(data, content_type="application/gzip")
        return f"gs://{self.bucket.name}/{key}"

    def put_many_json(self, items: dict[str, Any]) -> dict[str, str]:
        """Upload many payloads in parallel; return {key: gs:// path}.

        Used by the scraper, which writes up to a full CLOB page of new markets
        per request — sequential uploads would blow the dispatch deadline.
        """
        if not items:
            return {}
        keys = list(items)
        with ThreadPoolExecutor(max_workers=UPLOAD_CONCURRENCY) as pool:
            paths = pool.map(lambda k: self.put_json(k, items[k]), keys)
        return dict(zip(keys, paths, strict=True))
