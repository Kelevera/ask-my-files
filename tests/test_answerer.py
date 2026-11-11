import pytest

from askfiles import config, store
from askfiles.answerer import NOT_IN_DOCUMENTS, REFUSAL_MESSAGE, SYSTEM_PROMPT, Citation, answer
from askfiles.chunker import Chunk

# Chunk vectors chosen so that the query [1, 0] scores 1.0, 0.8, 0.6 and 0.0.
CHUNKS = [
    (Chunk("C:/docs/plan.pdf", "page 3", "The launch is in May."), [1.0, 0.0]),
    (Chunk("C:/docs/notes.docx", "section Budget", "The budget is 100."), [0.8, 0.6]),
    (Chunk("C:/docs/misc.txt", "", "Lunch is at noon."), [0.6, 0.8]),
    (Chunk("C:/docs/other.md", "", "Unrelated."), [0.0, 1.0]),
]


class FakeChat:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    def __call__(self, system, user):
        self.calls.append((system, user))
        return self.reply


def embed_strong(texts):
    return [[1.0, 0.0] for _ in texts]


def embed_weak(texts):
    # Best cosine against the chunks is 0.3, below the default minimum of 0.35.
    return [[-0.954, 0.3] for _ in texts]


@pytest.fixture
def db(tmp_path):
    connection = store.connect(tmp_path / "index.sqlite")
    for chunk, vector in CHUNKS:
        store.replace_chunks(connection, chunk.path, [chunk], [vector])
    yield connection
    connection.close()


def test_min_score_config():
    assert config.load({}).min_score == 0.35
    assert config.load({"ASKFILES_MIN_SCORE": "0.5"}).min_score == 0.5


def test_system_prompt_states_the_rules():
    assert "only" in SYSTEM_PROMPT
    assert "[n]" in SYSTEM_PROMPT
    assert NOT_IN_DOCUMENTS == "NOT_IN_DOCUMENTS"
    assert "exactly NOT_IN_DOCUMENTS" in SYSTEM_PROMPT


def test_prompt_lists_numbered_sources_and_the_question(db):
    chat = FakeChat("In May [1].")
    answer(db, embed_strong, chat, "When is the launch?", k=3)

    system, user = chat.calls[0]
    assert system == SYSTEM_PROMPT
    assert user.index("[1]") < user.index("The launch is in May.") < user.index("[2]")
    assert user.index("[2]") < user.index("The budget is 100.") < user.index("[3]")
    assert "[4]" not in user and "Unrelated." not in user
    assert "plan.pdf, page 3" in user
    assert user.rstrip().endswith("When is the launch?")


def test_answer_cites_the_sources_named_in_the_reply(db):
    result = answer(db, embed_strong, FakeChat("Launch in May [1], budget 100 [2] and [1]."),
                    "question", k=3)

    assert result.refused is False
    assert result.answer == "Launch in May [1], budget 100 [2] and [1]."
    assert result.citations == [
        Citation("C:/docs/plan.pdf", "page 3"),
        Citation("C:/docs/notes.docx", "section Budget"),
    ]
    assert result.scores == pytest.approx([1.0, 0.8, 0.6])
    assert [chunk.path for chunk in result.sources] == [c.path for c, _ in CHUNKS[:3]]


def test_only_cited_sources_are_listed(db):
    result = answer(db, embed_strong, FakeChat("The budget is 100 [2]."), "question", k=3)
    assert result.citations == [Citation("C:/docs/notes.docx", "section Budget")]


def test_without_valid_citation_the_top_two_sources_are_cited(db):
    # [7] does not exist among 3 sources, so it does not count as a citation.
    result = answer(db, embed_strong, FakeChat("The launch is in May [7]."), "question", k=3)
    assert result.citations == [
        Citation("C:/docs/plan.pdf", "page 3"),
        Citation("C:/docs/notes.docx", "section Budget"),
    ]


def test_refuses_by_score_without_calling_the_model(db):
    chat = FakeChat("should never be used")
    result = answer(db, embed_weak, chat, "question")

    assert chat.calls == []
    assert result.refused is True
    assert result.answer == REFUSAL_MESSAGE
    assert result.citations == []
    assert max(result.scores) == pytest.approx(0.3, abs=0.05)


def test_min_score_argument_overrides_the_threshold(db):
    chat = FakeChat("Something [1].")
    assert answer(db, embed_weak, chat, "question", min_score=0.1).refused is False
    assert answer(db, embed_strong, chat, "question", min_score=1.01).refused is True
    assert len(chat.calls) == 1


@pytest.mark.parametrize("reply", ["NOT_IN_DOCUMENTS", "  NOT_IN_DOCUMENTS.\n",
                                   "NOT_IN_DOCUMENTS [1]"])
def test_refuses_when_the_model_says_not_in_documents(db, reply):
    chat = FakeChat(reply)
    result = answer(db, embed_strong, chat, "question")

    assert len(chat.calls) == 1
    assert result.refused is True
    assert result.answer == REFUSAL_MESSAGE
    assert result.citations == []
    assert result.scores[0] == pytest.approx(1.0)


def test_empty_index_refuses_without_calling_the_model(tmp_path):
    connection = store.connect(tmp_path / "empty.sqlite")
    chat = FakeChat("unused")
    result = answer(connection, embed_strong, chat, "question")
    connection.close()

    assert (result.refused, result.citations, result.scores, chat.calls) == (True, [], [], [])
