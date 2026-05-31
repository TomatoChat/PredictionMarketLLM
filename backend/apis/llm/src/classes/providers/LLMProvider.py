from abc import ABC, abstractmethod
from functools import cached_property
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape

from db import LLMConfig

from ...models import LLMPredictionResult, MarketPromptContext

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


class LLMProvider(ABC):
    """Abstract base for every concrete LLM provider.

    Holds the shared Jinja environment used to render prompt templates from
    the sibling ``prompts/`` directory — subclasses access it as
    ``self.jinja_env``. Concrete providers (one class per file, see
    ``OpenAI.py``) implement ``predict`` and are wired into the registry in
    ``LLMRegistry.py``.
    """

    @cached_property
    def jinja_env(self) -> Environment:
        return Environment(
            loader=FileSystemLoader(_PROMPTS_DIR),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    @abstractmethod
    def predict(
        self, context: MarketPromptContext, config: LLMConfig
    ) -> LLMPredictionResult: ...
