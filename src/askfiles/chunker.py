"""Split segments into overlapping chunks. A chunk never spans two segments."""
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    path: str
    label: str
    text: str


def chunk_segments(segments, size=800, overlap=150):
    """Return chunks of at most `size` characters, each sharing `overlap` with the previous."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    chunks = []
    for segment in segments:
        start = 0
        while start < len(segment.text):
            chunks.append(Chunk(segment.path, segment.label, segment.text[start:start + size]))
            if start + size >= len(segment.text):
                break
            start += size - overlap
    return chunks
