"""A tiny structured request used by "Test provider" to prove the whole path works."""

import time

from pydantic import BaseModel, Field
from sqlmodel import SQLModel

from app.llm.base import ChatMessage, Provider, ProviderError
from app.llm.structured import StructuredOutputError, generate_structured


class ProbeAnswer(BaseModel):
    greeting: str = Field(description="One short friendly sentence.")
    sum: int = Field(description="The result of 17 + 25.")


class ProviderTestResult(SQLModel):
    ok: bool
    model: str | None
    latency_ms: int
    attempts: int = 0
    answer: ProbeAnswer | None = None
    # True when the model also got the arithmetic right, a cheap sanity check.
    correct: bool | None = None
    error: str | None = None


PROBE_MESSAGES: list[ChatMessage] = [
    {"role": "system", "content": "You are a JSON API. Reply only with JSON matching the given schema."},
    {"role": "user", "content": "Greet the user in one short sentence, and compute 17 + 25."},
]


def run_probe(provider: Provider) -> ProviderTestResult:
    start = time.monotonic()
    elapsed = lambda: int((time.monotonic() - start) * 1000)  # noqa: E731
    try:
        result = generate_structured(provider, ProbeAnswer, PROBE_MESSAGES)
    except StructuredOutputError as exc:
        return ProviderTestResult(
            ok=False, model=provider.model, latency_ms=elapsed(), attempts=exc.attempts, error=str(exc)
        )
    except ProviderError as exc:
        return ProviderTestResult(ok=False, model=provider.model, latency_ms=elapsed(), error=str(exc))
    return ProviderTestResult(
        ok=True,
        model=provider.model,
        latency_ms=elapsed(),
        attempts=result.attempts,
        answer=result.value,
        correct=result.value.sum == 42,
    )
