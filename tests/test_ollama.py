import io
import json
import urllib.error

import pytest

from askfiles import config, ollama


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class FakeServer:
    """Replaces urlopen. Routes are {path: handler(payload) -> dict or Exception}."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, request, timeout=None):
        path = request.full_url.split("11434", 1)[1]
        payload = json.loads(request.data) if request.data else None
        self.calls.append((request.get_method(), request.full_url, payload))
        if path not in self.routes:
            raise urllib.error.HTTPError(request.full_url, 404, "Not Found", {}, None)
        result = self.routes[path](payload)
        if isinstance(result, Exception):
            raise result
        return FakeResponse(json.dumps(result).encode("utf-8"))


@pytest.fixture
def client_with(monkeypatch):
    def make(routes):
        server = FakeServer(routes)
        monkeypatch.setattr(ollama.urllib.request, "urlopen", server)
        return ollama.OllamaClient(config.load({})), server
    return make


def test_config_defaults():
    cfg = config.load({})
    assert cfg.chat_model == "qwen2.5:7b"
    assert cfg.embed_model == "nomic-embed-text"
    assert cfg.ollama_url == "http://localhost:11434"


def test_config_reads_environment():
    cfg = config.load({
        "ASKFILES_CHAT_MODEL": "llama3",
        "ASKFILES_EMBED_MODEL": "bge-m3",
        "ASKFILES_OLLAMA_URL": "http://localhost:9999/",
    })
    assert (cfg.chat_model, cfg.embed_model) == ("llama3", "bge-m3")
    assert cfg.ollama_url == "http://localhost:9999"


def test_config_uses_os_environ_by_default(monkeypatch):
    monkeypatch.setenv("ASKFILES_CHAT_MODEL", "from-env")
    assert config.load().chat_model == "from-env"


def test_health_true_when_server_answers(client_with):
    client, server = client_with({"/api/tags": lambda p: {"models": []}})
    assert client.health() is True
    assert server.calls[0][:2] == ("GET", "http://localhost:11434/api/tags")


def test_health_false_when_server_is_down(client_with):
    client, _ = client_with({"/api/tags": lambda p: urllib.error.URLError("refused")})
    assert client.health() is False


def test_embed_uses_api_embed(client_with):
    client, server = client_with({
        "/api/embed": lambda p: {"embeddings": [[float(len(t)), 0.5] for t in p["input"]]},
    })
    assert client.embed(["a", "bbb"]) == [[1.0, 0.5], [3.0, 0.5]]
    method, url, payload = server.calls[0]
    assert method == "POST"
    assert payload == {"model": "nomic-embed-text", "input": ["a", "bbb"]}


def test_embed_empty_list_makes_no_call(client_with):
    client, server = client_with({})
    assert client.embed([]) == []
    assert server.calls == []


def test_embed_falls_back_to_api_embeddings_on_404(client_with):
    client, server = client_with({
        "/api/embeddings": lambda p: {"embedding": [float(len(p["prompt"]))]},
    })
    assert client.embed(["a", "bbb"]) == [[1.0], [3.0]]
    assert [c[1].rsplit("/", 1)[1] for c in server.calls] == ["embed", "embeddings", "embeddings"]
    assert server.calls[1][2] == {"model": "nomic-embed-text", "prompt": "a"}


def test_embed_raises_on_other_http_errors(client_with):
    error = urllib.error.HTTPError("u", 500, "boom", {}, None)
    client, server = client_with({"/api/embed": lambda p: error})
    with pytest.raises(urllib.error.HTTPError):
        client.embed(["a"])
    assert len(server.calls) == 1


def test_chat_sends_system_and_user_and_returns_content(client_with):
    client, server = client_with({
        "/api/chat": lambda p: {"message": {"role": "assistant", "content": "The answer [1]."}},
    })
    assert client.chat("be precise", "what?") == "The answer [1]."
    payload = server.calls[0][2]
    assert payload["model"] == "qwen2.5:7b"
    assert payload["stream"] is False
    assert payload["messages"] == [
        {"role": "system", "content": "be precise"},
        {"role": "user", "content": "what?"},
    ]
