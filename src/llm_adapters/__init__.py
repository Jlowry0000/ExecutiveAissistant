import os
from typing import Optional

from .base import LLMAdapter

_PROVIDERS: dict[str, type[LLMAdapter]] = {}


def register_provider(name: str):
    def decorator(cls: type[LLMAdapter]):
        _PROVIDERS[name] = cls
        return cls
    return decorator


def get_llm_adapter(
    provider: str,
    api_key: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs
) -> LLMAdapter:
    if provider not in _PROVIDERS:
        available = ", ".join(_PROVIDERS.keys())
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {available}"
        )

    init_kwargs = {}
    if api_key:
        init_kwargs["api_key"] = api_key
    if model:
        init_kwargs["model"] = model
    if base_url:
        init_kwargs["base_url"] = base_url

    return _PROVIDERS[provider](**init_kwargs, **kwargs)


def list_providers() -> list[str]:
    return list(_PROVIDERS.keys())


from .openai import OpenAIAdapter
from .ollama import OllamaAdapter
from .minimax import MiniMaxAdapter
from .deepseek import DeepSeekAdapter