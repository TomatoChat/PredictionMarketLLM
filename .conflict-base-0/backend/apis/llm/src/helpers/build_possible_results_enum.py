from enum import StrEnum


def build_possible_results_enum(outcome_labels: list[str]) -> type[StrEnum]:
    """Build a ``StrEnum`` whose members are the outcome labels of a market.

    Used as the type of ``MarketPredictionResponse.result`` so the LLM's
    structured-output schema constrains its answer to one of the listed labels
    (via Pydantic's generated JSON-Schema ``enum`` keyword).
    """
    if not outcome_labels:
        raise ValueError(
            "build_possible_results_enum requires at least one outcome label"
        )

    return StrEnum("PossibleResults", {label: label for label in outcome_labels})
