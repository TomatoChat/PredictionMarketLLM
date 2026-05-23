import logging
import time
from typing import Any

from py_clob_client_v2.client import ClobClient
from py_clob_client_v2.exceptions import PolyApiException

MAX_RETRIES = 4
BACKOFF_BASE_SECONDS = 2.0

logger = logging.getLogger(__name__)


def get_markets_with_retry(client: ClobClient, cursor: str) -> Any:
    """Call ClobClient.get_markets(cursor) with exponential-backoff retry on PolyApiException.

    Retries up to MAX_RETRIES times before re-raising the last exception.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.get_markets(cursor)
        except PolyApiException as exc:
            if attempt == MAX_RETRIES:
                raise

            wait = BACKOFF_BASE_SECONDS**attempt

            logger.warning(
                f"polymarket - get_markets failed (attempt {attempt}/{MAX_RETRIES}), "
                f"retrying in {wait:.1f}s: {exc}"
            )
            time.sleep(wait)

    raise RuntimeError("unreachable: MAX_RETRIES must be > 0")
