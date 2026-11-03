from collections.abc import Callable
from typing import Generic, TypeVar

T = TypeVar("T")


class ConfigurationError(Exception):
    """Invalid configuration at startup (unknown provider...)."""


class Registry(Generic[T]):
    """Adding a provider = registering a function; no `if` to change elsewhere (open/closed)."""

    def __init__(self, kind: str) -> None:
        self._kind = kind
        self._builders: dict[str, Callable[..., T]] = {}

    def register(self, name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def decorator(builder: Callable[..., T]) -> Callable[..., T]:
            self._builders[name] = builder
            return builder

        return decorator

    def build(self, name: str, *args, **kwargs) -> T:
        builder = self._builders.get(name)
        if builder is None:
            raise ConfigurationError(f"Unknown {self._kind} provider '{name}'. Available: {', '.join(self.names())}")
        return builder(*args, **kwargs)

    def names(self) -> list[str]:
        return sorted(self._builders)
