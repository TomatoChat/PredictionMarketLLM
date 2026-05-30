"""Entry point that reconciles every declared Qdrant collection against the cluster.

Run on deploy (see the ``qdrant_sync`` job in .github/workflows/deploy.yml) and
locally:

    PYTHONPATH=backend python -m qdrant.sync

Reads QDRANT_ENDPOINT / QDRANT_API_KEY from settings (env / .env locally, GSM on
Cloud Run). Idempotent — safe to run on every deploy.
"""

import logging

from . import COLLECTIONS, get_client, sync_collections

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )
    result = sync_collections(get_client(), COLLECTIONS)
    logger.info(f"qdrant sync complete: {result}")


if __name__ == "__main__":
    main()
