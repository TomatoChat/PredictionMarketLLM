from dataclasses import dataclass

from qdrant_client.models import PayloadSchemaType


@dataclass(frozen=True)
class PayloadIndex:
    """One payload field that Qdrant should index for fast filtering."""

    field_name: str
    field_schema: PayloadSchemaType
