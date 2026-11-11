import pytest

from askfiles import store
from askfiles.chunker import Chunk
from askfiles.retriever import top_k

VECTORS = {
    "east": [1.0, 0.0],
    "north-east": [1.0, 1.0],
    "north": [0.0, 1.0],
    "west": [-1.0, 0.0],
    "far east": [50.0, 0.0],
}


def embed(texts):
    return [VECTORS[text] for text in texts]


@pytest.fixture
def db(tmp_path):
    connection = store.connect(tmp_path / "index.sqlite")
    names = ["north", "west", "north-east", "far east"]
    for name in names:
        store.replace_chunks(connection, name + ".txt", [Chunk(name + ".txt", "page 1", name)],
                             [VECTORS[name]])
    yield connection
    connection.close()


def test_results_are_sorted_by_cosine_similarity(db):
    results = top_k(db, embed, "east", 4)

    assert [chunk.text for chunk, _ in results] == ["far east", "north-east", "north", "west"]
    scores = [score for _, score in results]
    # Cosine ignores vector length: [50, 0] is a perfect match for [1, 0].
    assert scores == pytest.approx([1.0, 0.7071068, 0.0, -1.0], abs=1e-6)
    assert all(isinstance(score, float) for score in scores)


def test_k_limits_the_number_of_results(db):
    results = top_k(db, embed, "north", 2)
    assert [chunk.text for chunk, _ in results] == ["north", "north-east"]


def test_k_larger_than_the_index_returns_everything(db):
    assert len(top_k(db, embed, "east", 99)) == 4


def test_results_keep_path_and_label(db):
    chunk, _ = top_k(db, embed, "west", 1)[0]
    assert (chunk.path, chunk.label) == ("west.txt", "page 1")


def test_empty_index_returns_no_results(tmp_path):
    connection = store.connect(tmp_path / "empty.sqlite")
    assert top_k(connection, embed, "east", 5) == []
    connection.close()


def test_zero_vector_scores_zero_instead_of_failing(db):
    store.replace_chunks(db, "zero.txt", [Chunk("zero.txt", "", "zero")], [[0.0, 0.0]])
    scores = {chunk.text: score for chunk, score in top_k(db, embed, "east", 9)}
    assert scores["zero"] == 0.0
