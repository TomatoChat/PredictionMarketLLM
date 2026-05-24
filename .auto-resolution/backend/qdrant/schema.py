from qdrant_client.models import Distance, PayloadSchemaType

from .consts import EMBEDDING_DIMS
from .models import CollectionSchema, PayloadIndex

MARKETS = CollectionSchema(
    name="markets",
    vector_size=EMBEDDING_DIMS,
    distance=Distance.COSINE,
    payload_indexes=(
        PayloadIndex(field_name="source", field_schema=PayloadSchemaType.KEYWORD),
    ),
)
