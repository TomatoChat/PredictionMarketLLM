from backend.llm.classes.providers.LLMProvider import LLMProvider
from backend.llm.classes.providers.OpenAI import OpenAI
from backend.supabase import LLMProvider as LLMProviderEnum

LLMRegistry: dict[LLMProviderEnum, LLMProvider] = {LLMProviderEnum.OPENAI: OpenAI()}
