import pytest

from askfiles import store
from askfiles.indexer import index_folder


class FakeEmbedder:
    def __init__(self):
        self.texts = []

    def __call__(self, texts):
        self.texts.extend(texts)
        return [[float(len(text)), 1.0] for text in texts]


@pytest.fixture
def db(tmp_path):
    connection = store.connect(tmp_path / "index.sqlite")
    yield connection
    connection.close()


@pytest.fixture
def folder(tmp_path):
    root = tmp_path / "docs"
    (root / "sub" / "deep").mkdir(parents=True)
    (root / "a.txt").write_text("alpha text", encoding="utf-8")
    (root / "sub" / "b.md").write_text("beta text", encoding="utf-8")
    (root / "sub" / "deep" / "c.txt").write_text("gamma text", encoding="utf-8")
    (root / "ignored.png").write_bytes(b"not a document")
    return root


def _texts(db):
    return sorted(chunk.text for chunk in store.all_chunks(db))


def test_first_run_adds_all_supported_files_recursively(db, folder):
    embed = FakeEmbedder()
    counts = index_folder(db, folder, embed)

    assert counts == {"added": 3, "updated": 0, "unchanged": 0, "removed": 0, "failed": 0}
    assert _texts(db) == ["alpha text", "beta text", "gamma text"]
    assert sorted(embed.texts) == ["alpha text", "beta text", "gamma text"]
    assert set(store.document_state(db)) == {
        str(folder / "a.txt"), str(folder / "sub" / "b.md"), str(folder / "sub" / "deep" / "c.txt")}
    chunk = next(c for c in store.all_chunks(db) if c.text == "alpha text")
    assert chunk.path == str(folder / "a.txt")
    assert list(chunk.embedding) == [10.0, 1.0]


def test_second_run_skips_unchanged_files_without_embedding(db, folder):
    index_folder(db, folder, FakeEmbedder())
    embed = FakeEmbedder()

    counts = index_folder(db, folder, embed)

    assert counts == {"added": 0, "updated": 0, "unchanged": 3, "removed": 0, "failed": 0}
    assert embed.texts == []


def test_changed_file_is_re_embedded_and_its_old_chunks_replaced(db, folder):
    index_folder(db, folder, FakeEmbedder())
    (folder / "a.txt").write_text("alpha text, second edition", encoding="utf-8")
    embed = FakeEmbedder()

    counts = index_folder(db, folder, embed)

    assert counts == {"added": 0, "updated": 1, "unchanged": 2, "removed": 0, "failed": 0}
    assert embed.texts == ["alpha text, second edition"]
    assert _texts(db) == ["alpha text, second edition", "beta text", "gamma text"]


def test_deleted_file_is_removed_from_the_index(db, folder):
    index_folder(db, folder, FakeEmbedder())
    (folder / "sub" / "b.md").unlink()

    counts = index_folder(db, folder, FakeEmbedder())

    assert counts == {"added": 0, "updated": 0, "unchanged": 2, "removed": 1, "failed": 0}
    assert _texts(db) == ["alpha text", "gamma text"]
    assert str(folder / "sub" / "b.md") not in store.document_state(db)


def test_chunk_settings_are_passed_to_the_chunker(db, folder):
    (folder / "long.txt").write_text("x" * 100, encoding="utf-8")
    index_folder(db, folder, FakeEmbedder(), chunk_size=40, chunk_overlap=10)
    assert len([c for c in store.all_chunks(db) if c.path.endswith("long.txt")]) == 3


def test_unreadable_file_is_counted_as_failed_and_the_rest_is_indexed(db, folder):
    (folder / "broken.pdf").write_bytes(b"this is not a pdf")

    counts = index_folder(db, folder, FakeEmbedder())

    assert counts == {"added": 3, "updated": 0, "unchanged": 0, "removed": 0, "failed": 1}
    assert str(folder / "broken.pdf") not in store.document_state(db)


def test_missing_folder_raises(db, tmp_path):
    with pytest.raises(NotADirectoryError):
        index_folder(db, tmp_path / "nope", FakeEmbedder())
