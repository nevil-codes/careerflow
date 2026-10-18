from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.llm.anthropic_provider import DEFAULT_MODEL, FALLBACK_BETA, AnthropicProvider, strict_schema
from app.llm.base import ProviderError, ProviderUnavailable
from app.llm.extract_posting import ExtractedPosting, extract_posting

REQUEST = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def text_response(text, stop_reason="end_turn"):
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=text)],
    )


class FakeClient:
    """Stands in for anthropic.Anthropic: records create() calls, replays scripted results."""

    def __init__(self, *results):
        self.results = list(results)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.models = SimpleNamespace(list=lambda: [SimpleNamespace(id="claude-sonnet-5-5"), SimpleNamespace(id="claude-opus-5-5")])

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        result = self.results.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def status_error(cls, code):
    return cls("boom", response=httpx2.Response(code, request=REQUEST), body=None)


def test_request_shape():
    client = FakeClient(text_response('{"a": 1}'))
    provider = AnthropicProvider(None, 30, client=client)

    reply = provider.chat(
        [{"role": "system", "content": "Be JSON."}, {"role": "user", "content": "hi"}],
        json_schema={"type": "object", "properties": {"a": {"type": "integer"}}},
    )

    assert reply == '{"a": 1}'  # thinking block ignored
    call = client.calls[0]
    assert call["model"] == DEFAULT_MODEL
    assert call["system"] == "Be JSON."
    assert call["messages"] == [{"role": "user", "content": "hi"}]
    assert call["betas"] == [FALLBACK_BETA]
    assert call["fallbacks"] == "default"
    fmt = call["output_config"]["format"]
    assert fmt["type"] == "json_schema"
    assert fmt["schema"]["additionalProperties"] is False
    assert fmt["schema"]["required"] == ["a"]


def test_no_schema_no_output_config():
    client = FakeClient(text_response("hello"))
    AnthropicProvider("claude-sonnet-5-5", 30, client=client).chat([{"role": "user", "content": "hi"}])
    assert "output_config" not in client.calls[0]
    assert "system" not in client.calls[0]
    assert client.calls[0]["model"] == "claude-sonnet-5-5"


@pytest.mark.parametrize(
    ("stop_reason", "message"), [("refusal", "declined"), ("max_tokens", "cut off")]
)
def test_bad_stop_reasons(stop_reason, message):
    client = FakeClient(text_response("", stop_reason))
    with pytest.raises(ProviderError, match=message):
        AnthropicProvider(None, 30, client=client).chat([{"role": "user", "content": "hi"}])


@pytest.mark.parametrize(
    ("error", "expected_type", "message"),
    [
        (anthropic.APIConnectionError(request=REQUEST), ProviderUnavailable, "Cannot reach the Anthropic API"),
        (anthropic.APITimeoutError(request=REQUEST), ProviderUnavailable, "Cannot reach the Anthropic API"),
        (status_error(anthropic.AuthenticationError, 401), ProviderError, "ANTHROPIC_API_KEY"),
        (status_error(anthropic.NotFoundError, 404), ProviderError, "Model not found"),
        (status_error(anthropic.RateLimitError, 429), ProviderError, "rate limit"),
        (status_error(anthropic.InternalServerError, 500), ProviderError, "error 500"),
    ],
)
def test_errors_are_translated(error, expected_type, message):
    provider = AnthropicProvider(None, 30, client=FakeClient(error))
    with pytest.raises(expected_type, match=message) as exc:
        provider.chat([{"role": "user", "content": "hi"}])
    assert type(exc.value) is expected_type


def test_list_models():
    assert AnthropicProvider(None, 30, client=FakeClient()).list_models() == ["claude-opus-5-5", "claude-sonnet-5-5"]


def test_strict_schema_keeps_a_property_named_default():
    schema = {"type": "object", "properties": {"default": {"type": "string", "default": "x"}}}
    out = strict_schema(schema)
    assert out["properties"]["default"] == {"type": "string"}
    assert out["required"] == ["default"]
    assert schema["properties"]["default"]["default"] == "x"  # input untouched


def test_extraction_end_to_end_through_claude_provider():
    jd = "Werkstudent (m/w/d) Data Engineering bei der Beispiel GmbH in Köln. Wir suchen dich für Python und SQL."
    reply = (
        '{"title_original": "Werkstudent (m/w/d) Data Engineering", "title_en": "Working Student Data Engineering",'
        ' "company": "Beispiel GmbH", "location_en": "Cologne, Germany", "language": "German", "url": null}'
    )
    client = FakeClient(text_response(reply))

    posting = extract_posting(AnthropicProvider(None, 30, client=client), jd)

    assert posting.to_posting_fields()["title"] == "Working Student Data Engineering"
    assert posting.to_posting_fields()["title_original"] == "Werkstudent (m/w/d) Data Engineering"
    schema = client.calls[0]["output_config"]["format"]["schema"]
    assert set(schema["required"]) == set(ExtractedPosting.model_fields)
