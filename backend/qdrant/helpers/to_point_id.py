from backend.supabase.consts import MARKET_ID_PREFIX


def to_point_id(market_id: str) -> str:
    """Convert a Postgres ``mkt_<uuid>`` market id into the bare UUID Qdrant uses as the point id."""
    return market_id.removeprefix(MARKET_ID_PREFIX)
