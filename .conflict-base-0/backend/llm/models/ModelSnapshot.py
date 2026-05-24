from enum import StrEnum

from backend.llm.models.Model import Model


class ModelSnapshot(StrEnum):
    """Pinned provider-specific model snapshot as used in ``llm_config.model_snapshot``.

    Each member maps to the ``Model`` family it belongs to via the ``model``
    property, so callers can pick a snapshot and derive the family with no
    duplication: ``ModelSnapshot.GPT_5_NANO_2025_08_07.model``.
    """

    GPT_5_NANO_2025_08_07 = "gpt-5-nano-2025-08-07"

    @property
    def model(self) -> Model:
        return MODEL_OF[self]


MODEL_OF: dict[ModelSnapshot, Model] = {
    ModelSnapshot.GPT_5_NANO_2025_08_07: Model.GPT_5_NANO,
}
