"""HTTP client for the local Ollama server (standard library only)."""
import json
import urllib.error
import urllib.request

TIMEOUT_SECONDS = 300


class OllamaClient:
    def __init__(self, config):
        self.config = config

    def _request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.ollama_url + path,
            data=data,
            headers={"Content-Type": "application/json"},
            method="GET" if payload is None else "POST",
        )
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.loads(response.read().decode("utf-8"))

    def health(self):
        """Return True when the Ollama server answers."""
        try:
            self._request("/api/tags")
            return True
        except (urllib.error.URLError, OSError, ValueError):
            return False

    def embed(self, texts):
        """Return one embedding (list of floats) per text."""
        if not texts:
            return []
        model = self.config.embed_model
        try:
            return self._request("/api/embed", {"model": model, "input": texts})["embeddings"]
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
        # D03: older Ollama versions only offer /api/embeddings, one text per call.
        return [
            self._request("/api/embeddings", {"model": model, "prompt": text})["embedding"]
            for text in texts
        ]

    def chat(self, system, user):
        """Return the model's reply to one system and one user message."""
        reply = self._request("/api/chat", {
            "model": self.config.chat_model,
            "stream": False,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        })
        return reply["message"]["content"]
