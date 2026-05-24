from enum import StrEnum


class Model(StrEnum):
    """Provider-specific model family/alias as used in ``llm_config.model``."""

    GPT_5_NANO = "gpt-5-nano"
