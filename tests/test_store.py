import sqlite3

import numpy as np
import pytest

from askfiles import store
from askfiles.chunker import Chunk


@pytest.fixture
def db(tmp_path):
    connection = store.connect(tmp_path / "index.sqlite")
    yield connection
    connection.close()


def test_connect_creates_the_tables(db):
    def columns(table):
        return [row[1] for row in db.execute(f"PRAGMA table_info({table})")]

    assert columns("documents") == ["path", "sha256", "mtime", "size"]
    assert columns("chunks") == ["id", "path", "label", "text", "embedding"]


def test_upsert_document_inserts_and_updates(db):
    store.upsert_document(db, "a.txt", "hash1", 1.5, 10)
    store.upsert_document(db, "b.txt", "hash2", 2.5, 20)
    store.upsert_document(db, "a.txt", "hash3", 3.5, 30)

    assert store.document_state(db) == {"a.txt": "hash3", "b.txt": "hash2"}
    assert db.execute("SELECT mtime, size FROM documents WHERE path='a.txt'").fetchone() == (3.5, 30)


def test_replace_chunks_stores_text_label_and_embedding(db):
    chunks = [Chunk("a.pdf", "page 1", "first"), Chunk("a.pdf", "page 2", "second")]
    store.replace_chunks(db, "a.pdf", chunks, [[0.1, 0.2, 0.3], [1.0, 2.0, 3.0]])

    stored = store.all_chunks(db)

    assert [(c.path, c.label, c.text) for c in stored] == [
        ("a.pdf", "page 1", "first"), ("a.pdf", "page 2", "second")]
    np.testing.assert_allclose(stored[0].embedding, [0.1, 0.2, 0.3], rtol=1e-6)
    np.testing.assert_allclose(stored[1].embedding, [1.0, 2.0, 3.0], rtol=1e-6)
    assert isinstance(db.execute("SELECT embedding FROM chunks").fetchone()[0], bytes)


def test_replace_chunks_replaces_only_that_document(db):
    store.replace_chunks(db, "a.txt", [Chunk("a.txt", "", "old 1"), Chunk("a.txt", "", "old 2")],
                         [[1.0], [2.0]])
    store.replace_chunks(db, "b.txt", [Chunk("b.txt", "", "keep")], [[3.0]])
    store.replace_chunks(db, "a.txt", [Chunk("a.txt", "", "new")], [[4.0]])

    assert sorted(c.text for c in store.all_chunks(db)) == ["keep", "new"]


def test_replace_chunks_rejects_mismatched_lengths(db):
    with pytest.raises(ValueError):
        store.replace_chunks(db, "a.txt", [Chunk("a.txt", "", "x")], [])


def test_delete_document_removes_document_and_chunks(db):
    for path in ["a.txt", "b.txt"]:
        store.upsert_document(db, path, "h", 1.0, 1)
        store.replace_chunks(db, path, [Chunk(path, "", "text")], [[1.0]])

    store.delete_document(db, "a.txt")

    assert store.document_state(db) == {"b.txt": "h"}
    assert [c.path for c in store.all_chunks(db)] == ["b.txt"]


def test_data_survives_reopening(tmp_path):
    path = tmp_path / "index.sqlite"
    first = store.connect(path)
    store.upsert_document(first, "a.txt", "h", 1.0, 1)
    store.replace_chunks(first, "a.txt", [Chunk("a.txt", "", "text")], [[1.0, 2.0]])
    first.close()

    second = sqlite3.connect(path)
    assert second.execute("SELECT COUNT(*) FROM chunks").fetchone() == (1,)
    second.close()
    reopened = store.connect(path)
    assert store.document_state(reopened) == {"a.txt": "h"}
    reopened.close()
