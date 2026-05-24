from functools import cached_property
from itertools import batched

import openai

from settings import get_settings

settings = get_settings()

EMBEDDING_MODEL = "text-embedding-3-large"
EMBEDDING_DIMS = 3072
EMBEDDING_BATCH_SIZE = 100


class Embedder:
    """Thin wrapper over the OpenAI embeddings API.

    One instance is constructed per scraper run; the SDK client is built lazily
    on first use and cached on the instance (same pattern as
    ``backend.llm.classes.providers.OpenAI.OpenAI``).
    """

    model: str = EMBEDDING_MODEL

    @cached_property
    def client(self) -> openai.OpenAI:
        return openai.OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one ``EMBEDDING_DIMS``-length vector per input string, preserving order."""
        if not texts:
            return []
        out: list[list[float]] = []
        for chunk in batched(texts, EMBEDDING_BATCH_SIZE):
            response = self.client.embeddings.create(
                model=self.model, input=list(chunk)
            )
            out.extend(item.embedding for item in response.data)
        return out

    @staticmethod
    def build_input(question: str, description: str | None) -> str:
        """Canonical input string fed to the embedder."""
        return f"{question}\n\n{description or ''}"
