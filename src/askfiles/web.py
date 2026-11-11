"""Local web page: a question box, the answer and its citations.

Run: python -m askfiles.web
"""
import urllib.error

from flask import Flask, render_template_string, request

from . import config, store
from .answerer import answer, describe
from .ollama import OllamaClient

HOST = "127.0.0.1"
PORT = 5000

PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Ask My Files</title>
<style>
body { font-family: Segoe UI, sans-serif; max-width: 46rem; margin: 2rem auto; padding: 0 1rem; }
input[type=text] { width: 80%; padding: .5rem; }
button { padding: .5rem 1rem; }
.answer { white-space: pre-wrap; background: #f4f4f4; padding: 1rem; border-radius: 6px; }
.error { color: #b00020; }
</style>
</head>
<body>
<h1>Ask My Files</h1>
<form method="post" action="/">
<input type="text" name="question" value="{{ question }}" placeholder="Ask a question about your documents" autofocus>
<button type="submit">Ask</button>
</form>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
{% if result %}
<h2>Answer</h2>
<div class="answer">{{ result.answer }}</div>
{% if citations %}
<h2>Sources</h2>
<ul>
{% for citation in citations %}<li>{{ citation }}</li>
{% endfor %}</ul>
{% endif %}
{% endif %}
</body>
</html>
"""


def create_app(client=None, db_path="index.sqlite"):
    cfg = config.load()
    client = client or OllamaClient(cfg)
    app = Flask(__name__, static_folder=None)  # no static route: files are never served

    @app.route("/", methods=["GET", "POST"])
    def index():
        question = request.form.get("question", "").strip()
        result, error = None, None
        if question:
            connection = store.connect(db_path)
            try:
                result = answer(connection, client.embed, client.chat, question,
                                min_score=cfg.min_score)
            except urllib.error.URLError as failure:
                error = (f"Ollama request to {cfg.ollama_url} failed: {failure}. "
                         "Is Ollama running, and are the models pulled?")
            finally:
                connection.close()
        citations = [describe(c.path, c.label) for c in result.citations] if result else []
        return render_template_string(PAGE, question=question, result=result, error=error,
                                      citations=citations)

    return app


if __name__ == "__main__":
    create_app().run(host=HOST, port=PORT)
