from typing import Any

from pydantic import BaseModel, Field


class LLMPredictionResult(BaseModel):
    """Provider-agnostic result of a single LLM call against one market.

    The model is contracted to pick exactly one outcome label, returned in
    ``result``. Operational metadata (raw payload, tool calls, token counts,
    latency) is captured here for persistence in the ``llm_prediction`` row.
    """

    result: str = Field(
        description="Outcome label the model selected; matches one of the market's outcome labels verbatim."
    )
    tool_calls: list[dict[str, Any]] | None = Field(
        default=None,
        description="Tool invocations made during the run (tool name, arguments, results) if any.",
    )
    raw_response: dict[str, Any] = Field(
        description="Full raw provider response, kept as an escape hatch for fields not yet normalized."
    )
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = Field(
        description="End-to-end latency of the provider call in milliseconds."
    )
