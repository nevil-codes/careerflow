"""Claude via the official Anthropic SDK.

Credentials come from the environment (ANTHROPIC_API_KEY, or an `ant auth login`
profile); they are never stored in the database.
"""

import copy

import anthropic

from app.llm.base import ChatMessage, ProviderError, ProviderUnavailable

DEFAULT_MODEL = "claude-opus-5-5"
# On a safety decline, the API re-runs the request on a suitable fallback model.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
NO_KEY_HINT = "Set ANTHROPIC_API_KEY in the backend's environment and restart it."


class AnthropicProvider:
    def __init__(self, model: str | None, timeout: float, client: anthropic.Anthropic | None = None) -> None:
        self.model = model or DEFAULT_MODEL
        self._client = client or anthropic.Anthropic(timeout=timeout)

    def chat(self, messages: list[ChatMessage], *, json_schema: dict | None = None) -> str:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        conversation = [m for m in messages if m["role"] != "system"]
        kwargs: dict = {}
        if system:
            kwargs["system"] = system
        if json_schema is not None:
            kwargs["output_config"] = {"format": {"type": "json_schema", "schema": strict_schema(json_schema)}}
        try:
            response = self._client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                messages=conversation,
                betas=[FALLBACK_BETA],
                fallbacks="default",
                **kwargs,
            )
        except Exception as exc:
            raise _translate(exc) from exc

        if response.stop_reason == "refusal":
            raise ProviderError("Claude declined this request.")
        if response.stop_reason == "max_tokens":
            raise ProviderError("Claude's reply was cut off (max_tokens).")
        return "".join(block.text for block in response.content if block.type == "text")

    def list_models(self) -> list[str]:
        try:
            return sorted(m.id for m in self._client.models.list())
        except Exception as exc:
            raise _translate(exc) from exc


def _translate(exc: Exception) -> ProviderError:
    """Map SDK errors onto the provider-neutral error types."""
    if isinstance(exc, (anthropic.APIConnectionError, anthropic.APITimeoutError)):
        return ProviderUnavailable(f"Cannot reach the Anthropic API: {exc}")
    if isinstance(exc, anthropic.AuthenticationError):
        return ProviderError(f"Anthropic rejected the API key. {NO_KEY_HINT}")
    if isinstance(exc, anthropic.PermissionDeniedError):
        return ProviderError("This API key isn't allowed to use that model.")
    if isinstance(exc, anthropic.NotFoundError):
        return ProviderError("Model not found. Pick one from the list in Settings.")
    if isinstance(exc, anthropic.RateLimitError):
        return ProviderError("Anthropic rate limit reached. Try again in a minute.")
    if isinstance(exc, anthropic.APIStatusError):
        return ProviderError(f"Anthropic API error {exc.status_code}: {exc.message}")
    if isinstance(exc, (anthropic.AnthropicError, TypeError)) and "auth" in str(exc).lower():
        return ProviderError(f"No Anthropic credentials found. {NO_KEY_HINT}")
    if isinstance(exc, anthropic.AnthropicError):
        return ProviderError(f"Anthropic SDK error: {exc}")
    raise exc


def strict_schema(schema: dict) -> dict:
    """Pydantic JSON schema -> the strict form structured outputs expect.

    Every object gets ``additionalProperties: false`` and lists all its properties as
    required; optional fields stay optional by being nullable (``anyOf [..., null]``).
    """
    schema = copy.deepcopy(schema)

    def visit(node: object) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object" and "properties" in node:
                node["additionalProperties"] = False
                node["required"] = list(node["properties"])
            for key, value in node.items():
                if key in ("properties", "$defs"):
                    # Maps of name -> schema: visit the schemas, not the names.
                    for sub in value.values():
                        visit(sub)
                else:
                    visit(value)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(schema)
    return schema
