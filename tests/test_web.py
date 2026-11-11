import urllib.error

import pytest

from askfiles import store, web
from askfiles.chunker import Chunk


class FakeClient:
    def __init__(self, reply="The launch is in <b>May</b> [1]."):
        self.reply = reply
        self.questions = []

    def embed(self, texts):
        return [[1.0, 0.0] for _ in texts]

    def chat(self, system, user):
        self.questions.append(user)
        return self.reply


class DownClient:
    def embed(self, texts):
        raise urllib.error.URLError("connection refused")

    def chat(self, system, user):
        raise urllib.error.URLError("connection refused")


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "index.sqlite"
    connection = store.connect(path)
    file = str(tmp_path / "docs" / "plan.pdf")
    store.replace_chunks(connection, file, [Chunk(file, "page 3", "The launch is in May.")],
                         [[1.0, 0.0]])
    file = str(tmp_path / "docs" / "notes.docx")
    store.replace_chunks(connection, file, [Chunk(file, "section Budget", "Budget is 100.")],
                         [[0.9, 0.1]])
    connection.close()
    return path


def _client(db_path, fake):
    return web.create_app(client=fake, db_path=db_path).test_client()


def test_binds_to_localhost_port_5000():
    assert (web.HOST, web.PORT) == ("127.0.0.1", 5000)


def test_page_shows_a_question_box(db_path):
    response = _client(db_path, FakeClient()).get("/")
    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '<form method="post"' in html
    assert 'name="question"' in html
    assert "Sources" not in html


def test_query_shows_the_answer_and_the_cited_source(db_path):
    fake = FakeClient()
    response = _client(db_path, fake).post("/", data={"question": "When is the launch?"})
    html = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "When is the launch?" in fake.questions[0]
    assert "The launch is in &lt;b&gt;May&lt;/b&gt; [1]." in html  # model output is escaped
    assert "<li>plan.pdf, page 3</li>" in html
    assert "notes.docx" not in html  # not cited
    assert 'value="When is the launch?"' in html
    assert str(db_path.parent) not in html  # no full paths, only file names


def test_section_citation_format(db_path):
    html = _client(db_path, FakeClient("Budget is 100 [2].")).post(
        "/", data={"question": "budget?"}).get_data(as_text=True)
    assert "<li>notes.docx, section Budget</li>" in html


def test_refusal_shows_the_message_without_sources(db_path):
    html = _client(db_path, FakeClient("NOT_IN_DOCUMENTS")).post(
        "/", data={"question": "What is the moon made of?"}).get_data(as_text=True)
    assert "I cannot find the answer in your documents." in html
    assert "<li>" not in html


def test_blank_question_does_not_call_the_model(db_path):
    fake = FakeClient()
    response = _client(db_path, fake).post("/", data={"question": "   "})
    assert response.status_code == 200
    assert fake.questions == []


def test_ollama_error_is_shown_on_the_page(db_path):
    response = _client(db_path, DownClient()).post("/", data={"question": "anything"})
    assert response.status_code == 200
    assert "Ollama" in response.get_data(as_text=True)


def test_files_are_not_served(db_path):
    client = _client(db_path, FakeClient())
    for url in ["/static/style.css", "/docs/plan.pdf", "/plan.pdf", "/index.sqlite",
                f"/{db_path.parent.as_posix()}/docs/plan.pdf"]:
        assert client.get(url).status_code == 404
