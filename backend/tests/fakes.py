from collections.abc import Callable

from app.llm.base import ChatMessage, ProviderError


class FakeProvider:
    """Returns scripted replies in order; a callable reply can inspect the request or raise."""

    def __init__(self, *replies: str | Callable[[list[ChatMessage]], str], model: str = "fake") -> None:
        self.replies = list(replies)
        self.model = model
        self.calls: list[tuple[list[ChatMessage], dict | None]] = []

    def chat(self, messages: list[ChatMessage], *, json_schema: dict | None = None) -> str:
        self.calls.append((list(messages), json_schema))
        if not self.replies:
            raise ProviderError("FakeProvider ran out of replies")
        reply = self.replies.pop(0)
        return reply(messages) if callable(reply) else reply

    def list_models(self) -> list[str]:
        return ["fake"]
