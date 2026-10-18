from typing import Literal, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: Literal["system", "user", "assistant"]
    content: str


class ProviderError(RuntimeError):
    """The provider was reached but the call failed (bad model, server error, ...)."""


class ProviderUnavailable(ProviderError):
    """The provider could not be reached at all."""


class Provider(Protocol):
    model: str | None

    def chat(self, messages: list[ChatMessage], *, json_schema: dict | None = None) -> str:
        """Return the assistant's reply text. With ``json_schema``, ask for JSON matching it."""
        ...

    def list_models(self) -> list[str]: ...
