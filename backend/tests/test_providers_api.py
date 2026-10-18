import pytest

from app.api import providers as providers_api
from app.config import OLLAMA_URL
from app.llm.base import ProviderUnavailable
from tests.fakes import FakeProvider


def create(client, **body):
    res = client.post("/providers", json={"name": "Local"} | body)
    assert res.status_code == 201, res.text
    return res.json()


def use_fake(monkeypatch, fake):
    monkeypatch.setattr(providers_api, "build_provider", lambda _config: fake)


def test_create_defaults_to_ollama_url(client):
    config = create(client)
    assert config["provider"] == "ollama"
    assert config["base_url"] == OLLAMA_URL
    assert config["enabled"] is False
    assert client.get("/providers").json() == [config]
    assert client.get("/providers/defaults").json() == {"base_urls": {"ollama": OLLAMA_URL, "anthropic": None}}


@pytest.mark.parametrize(
    "body",
    [
        {"name": " "},
        {"name": "x", "provider": "openai"},
        {"name": "x", "base_url": "localhost:11434"},
    ],
)
def test_create_validation(client, body):
    assert client.post("/providers", json=body).status_code == 422


def test_duplicate_name_conflicts(client):
    create(client)
    assert client.post("/providers", json={"name": "Local"}).status_code == 409


def test_only_one_provider_enabled(client):
    a = create(client, name="A", enabled=True)
    b = create(client, name="B", enabled=True)

    enabled = {p["name"]: p["enabled"] for p in client.get("/providers").json()}
    assert enabled == {"A": False, "B": True}

    client.patch(f"/providers/{a['id']}", json={"enabled": True})
    enabled = {p["name"]: p["enabled"] for p in client.get("/providers").json()}
    assert enabled == {"A": True, "B": False}

    client.patch(f"/providers/{b['id']}", json={"model": "qwen3:8b"})
    assert client.get("/providers").json()[0]["enabled"] is True


def test_update_and_delete(client):
    config = create(client)

    res = client.patch(f"/providers/{config['id']}", json={"model": "gpt-oss:20b", "base_url": "http://gpu:11434"})
    assert res.json()["model"] == "gpt-oss:20b"
    assert res.json()["base_url"] == "http://gpu:11434"
    assert client.patch(f"/providers/{config['id']}", json={"base_url": None}).status_code == 422
    assert client.patch(f"/providers/{config['id']}", json={"name": ""}).status_code == 422

    assert client.delete(f"/providers/{config['id']}").status_code == 204
    assert client.get("/providers").json() == []


def test_test_endpoint_success(client, monkeypatch):
    fake = FakeProvider('{"greeting": "Hi!", "sum": 42}', model="gpt-oss:20b")
    use_fake(monkeypatch, fake)

    body = client.post(f"/providers/{create(client)['id']}/test").json()

    assert body["ok"] is True
    assert body["correct"] is True
    assert body["attempts"] == 1
    assert body["answer"] == {"greeting": "Hi!", "sum": 42}
    assert body["model"] == "gpt-oss:20b"


def test_test_endpoint_reports_invalid_output(client, monkeypatch):
    use_fake(monkeypatch, FakeProvider("nope", "nope", "nope"))

    body = client.post(f"/providers/{create(client)['id']}/test").json()

    assert body["ok"] is False
    assert body["attempts"] == 3
    assert "No valid output" in body["error"]


def test_test_endpoint_reports_unreachable(client, monkeypatch):
    def down(_messages):
        raise ProviderUnavailable("Cannot reach Ollama")

    use_fake(monkeypatch, FakeProvider(down))

    body = client.post(f"/providers/{create(client)['id']}/test").json()

    assert body == body | {"ok": False, "error": "Cannot reach Ollama", "attempts": 0}


def test_models_endpoint(client, monkeypatch):
    config = create(client)
    use_fake(monkeypatch, FakeProvider())
    assert client.get(f"/providers/{config['id']}/models").json() == ["fake"]

    class Down(FakeProvider):
        def list_models(self):
            raise ProviderUnavailable("Cannot reach Ollama")

    use_fake(monkeypatch, Down())
    res = client.get(f"/providers/{config['id']}/models")
    assert res.status_code == 503
    assert res.json()["detail"] == "Cannot reach Ollama"


def test_missing_provider_is_404(client):
    assert client.post("/providers/9/test").status_code == 404
    assert client.get("/providers/9/models").status_code == 404


def test_create_anthropic_provider_has_no_url(client):
    config = create(client, name="Claude", provider="anthropic", model="claude-opus-5-5")
    assert config["provider"] == "anthropic"
    assert config["base_url"] is None
    assert client.get("/providers/defaults").json()["base_urls"]["anthropic"] is None
