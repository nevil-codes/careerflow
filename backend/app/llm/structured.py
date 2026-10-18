"""Structured output: ask for JSON matching a Pydantic model, validate, retry with feedback."""

import re
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from app.llm.base import ChatMessage, Provider, ProviderError

_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


class StructuredOutputError(ProviderError):
    def __init__(self, message: str, attempts: int, raw: str) -> None:
        super().__init__(message)
        self.attempts = attempts
        self.raw = raw


@dataclass
class StructuredResult[T: BaseModel]:
    value: T
    attempts: int
    raw: str


def generate_structured[T: BaseModel](
    provider: Provider,
    output_model: type[T],
    messages: list[ChatMessage],
    *,
    max_attempts: int = 3,
) -> StructuredResult[T]:
    """Validated output or ``StructuredOutputError``. Connection errors are not retried."""
    schema = output_model.model_json_schema()
    conversation = list(messages)
    raw = ""
    error = ""
    for attempt in range(1, max_attempts + 1):
        raw = provider.chat(conversation, json_schema=schema)
        try:
            return StructuredResult(output_model.model_validate_json(_unfence(raw)), attempt, raw)
        except ValidationError as exc:
            error = _summarize(exc)
            conversation += [
                {"role": "assistant", "content": raw},
                {
                    "role": "user",
                    "content": f"That reply was invalid: {error}. "
                    "Reply again with only JSON that matches the schema.",
                },
            ]
    raise StructuredOutputError(
        f"No valid output after {max_attempts} attempts. Last error: {error}", max_attempts, raw
    )


def _unfence(raw: str) -> str:
    match = _FENCE.match(raw)
    return match.group(1) if match else raw


def _summarize(exc: ValidationError) -> str:
    return "; ".join(
        f"{'.'.join(map(str, e['loc'])) or 'reply'}: {e['msg']}" for e in exc.errors()[:5]
    )
