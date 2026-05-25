import time
from functools import cached_property

import openai
from pydantic import create_model

from ...helpers import build_possible_results_enum
from ...models import (
    KwargsOpenAI,
    LLMPredictionResult,
    MarketPromptContext,
)
from .LLMProvider import LLMProvider
from supabase import LLMConfig
from settings import get_settings


class OpenAI(LLMProvider):
    """Calls the OpenAI Responses API with a per-market Pydantic ``text_format``.

    ``config.tools`` is passed through verbatim (already in OpenAI shape, e.g.
    ``[{"type": "web_search"}]``). ``config.extra`` is spread as keyword args,
    so reasoning effort, seed, service_tier, etc. live there. The SDK client
    is built lazily on first use and cached on the instance — the provider
    registry constructs one ``OpenAI()`` so the client is effectively a
    singleton in practice. ``jinja_env`` is inherited from ``LLMProvider``.
    """

    @cached_property
    def client(self) -> openai.OpenAI:
        return openai.OpenAI(
            api_key=get_settings().OPENAI_API_KEY.get_secret_value()
        )

    def predict(
        self, context: MarketPromptContext, config: LLMConfig
    ) -> LLMPredictionResult:
        context_data = context.model_dump()
        kwargs = KwargsOpenAI(
            model=config.model_snapshot or config.model,
            input=[
                {
                    "role": "system",
                    "content": self.jinja_env.get_template("system.j2").render(
                        **context_data
                    ),
                },
                {
                    "role": "user",
                    "content": self.jinja_env.get_template(
                        "market_prediction.j2"
                    ).render(**context_data),
                },
            ],
            text_format=create_model(
                "MarketPredictionResponse",
                result=(build_possible_results_enum(context.outcome_labels), ...),
            ),
            tools=list(config.tools) if config.tools else None,
            temperature=float(config.temperature)
            if config.temperature is not None
            else None,
            top_p=float(config.top_p) if config.top_p is not None else None,
            max_output_tokens=config.max_tokens,
            extra=dict(config.extra) if config.extra else {},
        )

        started = time.perf_counter()
        response = self.client.responses.parse(**kwargs.to_kwargs())
        raw = response.model_dump(warnings=False)

        if response.output_parsed is None:
            raise RuntimeError(
                f"OpenAI Responses API returned no parsed output for model {config.model}; raw status={raw.get('status')}"  # noqa: E501
            )

        return LLMPredictionResult(
            result=response.output_parsed.model_dump()["result"],
            tool_calls=[
                item for item in raw.get("output", []) if item.get("type") != "message"
            ]
            or None,
            raw_response=raw,
            input_tokens=(raw.get("usage") or {}).get("input_tokens"),
            output_tokens=(raw.get("usage") or {}).get("output_tokens"),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
