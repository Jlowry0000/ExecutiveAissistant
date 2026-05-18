from abc import ABC, abstractmethod
from typing import Any, TypeVar

T = TypeVar("T", bound="LLMAdapter")

_PROVIDERS: dict[str, type["LLMAdapter"]] = {}


def register_provider(name: str):
    def decorator(cls: type[T]) -> type[T]:
        _PROVIDERS[name] = cls
        return cls
    return decorator


class LLMAdapter(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[dict[str, str]],
        json_output: bool = False,
        **kwargs
    ) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def provider_name(self) -> str:
        raise NotImplementedError