from abc import ABC, abstractmethod
from functools import cached_property

from jinja2 import Environment, PackageLoader, StrictUndefined, select_autoescape

from backend.llm.models import LLMPredictionResult, MarketPromptContext
from backend.supabase import LLMConfig


class LLMProvider(ABC):
    """Abstract base for every concrete LLM provider.

    Holds the shared Jinja environment used to render prompt templates from
    ``backend/llm/prompts/`` — subclasses access it as ``self.jinja_env``.
    Concrete providers (one class per file, see ``OpenAI.py``) implement
    ``predict`` and are wired into the registry in ``LLMRegistry.py``.
    """

    @cached_property
    def jinja_env(self) -> Environment:
        return Environment(
            loader=PackageLoader("backend.llm", "prompts"),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=True,
        )

    @abstractmethod
    def predict(
        self, context: MarketPromptContext, config: LLMConfig
    ) -> LLMPredictionResult: ...
