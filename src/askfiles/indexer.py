"""Incremental indexing of a folder into the store."""
import hashlib
import logging
import os

from . import config, store
from .chunker import chunk_segments
from .loaders import SUPPORTED_EXTENSIONS, load_file

EMBED_BATCH = 32
log = logging.getLogger(__name__)


def _sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _walk(folder):
    for directory, _, names in os.walk(folder):
        for name in sorted(names):
            if os.path.splitext(name)[1].lower() in SUPPORTED_EXTENSIONS:
                yield os.path.join(directory, name)


def index_folder(connection, folder, embed, chunk_size=config.CHUNK_SIZE,
                 chunk_overlap=config.CHUNK_OVERLAP):
    """Bring the index up to date with the folder.

    embed is a function: list of strings -> list of vectors.
    Returns the counts added, updated, unchanged, removed and failed.
    """
    folder = os.path.abspath(folder)
    if not os.path.isdir(folder):
        raise NotADirectoryError(folder)
    counts = {"added": 0, "updated": 0, "unchanged": 0, "removed": 0, "failed": 0}
    known = store.document_state(connection)

    for path in _walk(folder):
        sha256 = _sha256(path)
        if known.get(path) == sha256:
            counts["unchanged"] += 1
            continue
        try:
            segments = load_file(path)
        except Exception as error:  # parser errors differ per library; report and go on
            log.warning("Cannot read %s: %s", path, error)
            counts["failed"] += 1
            continue
        chunks = chunk_segments(segments, chunk_size, chunk_overlap)
        embeddings = []
        for start in range(0, len(chunks), EMBED_BATCH):
            embeddings.extend(embed([c.text for c in chunks[start:start + EMBED_BATCH]]))
        store.replace_chunks(connection, path, chunks, embeddings)
        stat = os.stat(path)
        store.upsert_document(connection, path, sha256, stat.st_mtime, stat.st_size)
        counts["updated" if path in known else "added"] += 1

    for path in known:
        if not os.path.isfile(path):
            store.delete_document(connection, path)
            counts["removed"] += 1
    return counts
