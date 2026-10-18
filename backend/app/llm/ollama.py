"""Ollama client over its HTTP API, using only the standard library."""

import json
import urllib.error
import urllib.request
from typing import Any

from app.llm.base import ChatMessage, ProviderError, ProviderUnavailable


class OllamaProvider:
    def __init__(self, base_url: str, model: str | None, timeout: float) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[ChatMessage], *, json_schema: dict | None = None) -> str:
        if not self.model:
            raise ProviderError("No model selected for this provider.")
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            # Deterministic output: we want extraction, not creativity.
            "options": {"temperature": 0},
        }
        if json_schema is not None:
            body["format"] = json_schema
        data = self._request("POST", "/api/chat", body)
        try:
            return data["message"]["content"]
        except (KeyError, TypeError):
            raise ProviderError(f"Unexpected Ollama response: {str(data)[:200]}") from None

    def list_models(self) -> list[str]:
        data = self._request("GET", "/api/tags")
        return sorted(m["name"] for m in data.get("models", []))

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(
            f"{self.base_url}{path}",
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return json.loads(res.read())
        except urllib.error.HTTPError as exc:
            raise ProviderError(_http_error_message(exc, self.model)) from exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
            reason = getattr(exc, "reason", exc)
            raise ProviderUnavailable(
                f"Cannot reach Ollama at {self.base_url} ({reason}). Is `ollama serve` running?"
            ) from exc
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Ollama returned invalid JSON: {exc}") from exc


def _http_error_message(exc: urllib.error.HTTPError, model: str | None) -> str:
    try:
        detail = json.loads(exc.read()).get("error", "")
    except Exception:
        detail = ""
    if exc.code == 404 and "not found" in detail:
        return f"Model {model!r} is not installed. Run `ollama pull {model}`."
    return f"Ollama error {exc.code}: {detail or exc.reason}"
