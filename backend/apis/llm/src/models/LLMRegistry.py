from ..classes.providers.LLMProvider import LLMProvider
from ..classes.providers.OpenAI import OpenAI
from db import LLMProvider as LLMProviderEnum

LLMRegistry: dict[LLMProviderEnum, LLMProvider] = {LLMProviderEnum.OPENAI: OpenAI()}
