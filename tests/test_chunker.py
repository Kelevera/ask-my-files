import pytest

from askfiles.chunker import Chunk, chunk_segments
from askfiles.loaders import Segment


def _text(length):
    # Non-repeating text, so that positions can be found again with str.index.
    return "".join(f"{i:05d}" for i in range(length // 5 + 1))[:length]


def test_empty_input():
    assert chunk_segments([]) == []
    assert chunk_segments([Segment("a.txt", "", "")]) == []


def test_short_segment_is_one_chunk_with_path_and_label():
    chunks = chunk_segments([Segment("a.pdf", "page 2", "short text")])
    assert chunks == [Chunk("a.pdf", "page 2", "short text")]


def test_default_size_and_overlap():
    text = _text(2000)
    chunks = chunk_segments([Segment("a.txt", "", text)])

    assert all(len(c.text) <= 800 for c in chunks)
    assert len(chunks[0].text) == 800
    for previous, current in zip(chunks, chunks[1:]):
        assert previous.text[-150:] == current.text[:150]
    # Stitching the chunks without their overlap restores the full text.
    assert chunks[0].text + "".join(c.text[150:] for c in chunks[1:]) == text


def test_custom_size_and_overlap_cover_the_text_without_tiny_tail():
    text = _text(100)
    chunks = chunk_segments([Segment("a.txt", "", text)], size=40, overlap=10)
    assert [text.index(c.text) for c in chunks] == [0, 30, 60]
    assert [len(c.text) for c in chunks] == [40, 40, 40]


def test_chunks_never_cross_segment_boundaries():
    segments = [
        Segment("a.pdf", "page 1", "A" * 1000),
        Segment("a.pdf", "page 2", "B" * 1000),
    ]
    chunks = chunk_segments(segments)
    assert {c.label for c in chunks} == {"page 1", "page 2"}
    for chunk in chunks:
        expected = "A" if chunk.label == "page 1" else "B"
        assert set(chunk.text) == {expected}
        assert chunk.path == "a.pdf"


def test_overlap_must_be_smaller_than_size():
    with pytest.raises(ValueError):
        chunk_segments([Segment("a.txt", "", "abc")], size=10, overlap=10)
