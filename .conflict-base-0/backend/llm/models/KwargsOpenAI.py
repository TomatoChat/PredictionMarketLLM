from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class KwargsOpenAI(BaseModel):
    """Typed kwargs handed to ``openai.OpenAI.responses.parse(...)``.

    Captures the fields ``OpenAI.predict`` actually uses (a strict subset of
    the full Responses API surface). ``extra`` carries any provider-specific
    knobs stored in ``llm_config.extra`` (``reasoning``, ``seed``,
    ``service_tier``, ...) and is spread into the final kwargs dict.

    Use :meth:`to_kwargs` to produce the ``**kwargs`` dict; ``None`` fields
    are dropped so the SDK falls back to its own defaults.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    model: str
    input: list[dict[str, Any]]
    text_format: type[BaseModel]
    tools: list[dict[str, Any]] | None = None
    temperature: float | None = None
    top_p: float | None = None
    max_output_tokens: int | None = None
    extra: dict[str, Any] = Field(default_factory=dict)

    def to_kwargs(self) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "input": self.input,
            "text_format": self.text_format,
        }
        if self.tools is not None:
            kwargs["tools"] = self.tools

        if self.temperature is not None:
            kwargs["temperature"] = self.temperature

        if self.top_p is not None:
            kwargs["top_p"] = self.top_p

        if self.max_output_tokens is not None:
            kwargs["max_output_tokens"] = self.max_output_tokens

        kwargs.update(self.extra)

        return kwargs
