import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.llm.base import ProviderError, ProviderUnavailable
from app.llm.ollama import OllamaProvider


class StubOllama(BaseHTTPRequestHandler):
    """Speaks just enough of the Ollama API. Records requests on the server."""

    def do_GET(self):
        if self.path == "/api/tags":
            self._reply(200, {"models": [{"name": "zeta:1b"}, {"name": "alpha:7b"}]})
        else:
            self._reply(404, {"error": "not found"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.server.requests.append(body)
        if body["model"] == "missing":
            self._reply(404, {"error": f"model '{body['model']}' not found"})
        elif body["model"] == "broken":
            self._reply(500, {"error": "boom"})
        else:
            self._reply(200, {"message": {"role": "assistant", "content": '{"ok": true}'}})

    def _reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


@pytest.fixture
def stub():
    server = HTTPServer(("127.0.0.1", 0), StubOllama)
    server.requests = []
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    yield server
    server.shutdown()


def provider(stub, model="llama3:8b"):
    return OllamaProvider(f"http://127.0.0.1:{stub.server_port}/", model, timeout=5)


def test_chat_sends_schema_and_zero_temperature(stub):
    schema = {"type": "object"}
    reply = provider(stub).chat([{"role": "user", "content": "hi"}], json_schema=schema)

    assert reply == '{"ok": true}'
    sent = stub.requests[0]
    assert sent["model"] == "llama3:8b"
    assert sent["stream"] is False
    assert sent["format"] == schema
    assert sent["options"] == {"temperature": 0}
    assert sent["messages"] == [{"role": "user", "content": "hi"}]


def test_chat_without_schema_omits_format(stub):
    provider(stub).chat([{"role": "user", "content": "hi"}])
    assert "format" not in stub.requests[0]


def test_list_models_sorted(stub):
    assert provider(stub).list_models() == ["alpha:7b", "zeta:1b"]


def test_missing_model_suggests_pull(stub):
    with pytest.raises(ProviderError, match="ollama pull missing"):
        provider(stub, "missing").chat([{"role": "user", "content": "hi"}])


def test_server_error(stub):
    with pytest.raises(ProviderError, match="500: boom"):
        provider(stub, "broken").chat([{"role": "user", "content": "hi"}])


def test_no_model_selected(stub):
    with pytest.raises(ProviderError, match="No model selected"):
        provider(stub, None).chat([{"role": "user", "content": "hi"}])
    assert stub.requests == []


def test_unreachable_server():
    with pytest.raises(ProviderUnavailable, match="Cannot reach Ollama"):
        OllamaProvider("http://127.0.0.1:9", "m", timeout=2).list_models()
