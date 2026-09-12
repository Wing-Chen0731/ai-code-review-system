from collections.abc import Callable
from typing import Any

from .adapters.base import BaseProvider


class ProviderFactory:
    _providers: dict[str, type[BaseProvider]] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseProvider]) -> None:
        cls._providers[name] = provider_class

    @classmethod
    def create(cls, name: str, **kwargs: Any) -> BaseProvider:
        try:
            provider_class = cls._providers[name]
        except KeyError as exc:
            raise ValueError(f"Unknown provider: {name}") from exc
        return provider_class(**kwargs)

    @classmethod
    def registered(cls) -> tuple[str, ...]:
        return tuple(sorted(cls._providers))

