import pytest
from pydantic import BaseModel

from app.llm.base import ProviderUnavailable
from app.llm.structured import StructuredOutputError, generate_structured
from tests.fakes import FakeProvider

MESSAGES = [{"role": "user", "content": "go"}]


class Answer(BaseModel):
    name: str
    score: int


def test_valid_first_reply():
    provider = FakeProvider('{"name": "a", "score": 3}')

    result = generate_structured(provider, Answer, MESSAGES)

    assert result.value == Answer(name="a", score=3)
    assert result.attempts == 1
    _, schema = provider.calls[0]
    assert schema == Answer.model_json_schema()


def test_retries_with_validation_feedback():
    provider = FakeProvider('{"name": "a", "score": "high"}', "not json", '{"name": "a", "score": 7}')

    result = generate_structured(provider, Answer, MESSAGES)

    assert result.value.score == 7
    assert result.attempts == 3
    second_request, _ = provider.calls[1]
    assert second_request[0] == MESSAGES[0]
    assert second_request[1] == {"role": "assistant", "content": '{"name": "a", "score": "high"}'}
    assert "score" in second_request[2]["content"]
    assert second_request[2]["role"] == "user"


def test_markdown_fenced_json_is_accepted():
    provider = FakeProvider('```json\n{"name": "a", "score": 1}\n```')
    assert generate_structured(provider, Answer, MESSAGES).value.score == 1


def test_gives_up_after_max_attempts():
    provider = FakeProvider("{}", "{}")

    with pytest.raises(StructuredOutputError) as exc:
        generate_structured(provider, Answer, MESSAGES, max_attempts=2)

    assert exc.value.attempts == 2
    assert exc.value.raw == "{}"
    assert "name" in str(exc.value)


def test_unavailable_provider_is_not_retried():
    def down(_messages):
        raise ProviderUnavailable("down")

    provider = FakeProvider(down, '{"name": "a", "score": 1}')

    with pytest.raises(ProviderUnavailable):
        generate_structured(provider, Answer, MESSAGES)
    assert len(provider.calls) == 1
