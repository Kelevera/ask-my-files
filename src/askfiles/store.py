"""SQLite storage for documents and their embedded chunks."""
import sqlite3
from dataclasses import dataclass

import numpy as np

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    path TEXT PRIMARY KEY, sha256 TEXT, mtime REAL, size INTEGER);
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY, path TEXT, label TEXT, text TEXT, embedding BLOB);
CREATE INDEX IF NOT EXISTS chunks_path ON chunks(path);
"""


@dataclass(frozen=True, eq=False)
class StoredChunk:
    path: str
    label: str
    text: str
    embedding: np.ndarray


def connect(db_path):
    """Open the database at db_path and create the tables when they are missing."""
    connection = sqlite3.connect(str(db_path))
    connection.executescript(_SCHEMA)
    return connection


def upsert_document(connection, path, sha256, mtime, size):
    with connection:
        connection.execute(
            "INSERT OR REPLACE INTO documents (path, sha256, mtime, size) VALUES (?, ?, ?, ?)",
            (path, sha256, mtime, size))


def replace_chunks(connection, path, chunks, embeddings):
    """Replace all chunks of one document. embeddings holds one vector per chunk."""
    if len(chunks) != len(embeddings):
        raise ValueError("chunks and embeddings must have the same length")
    rows = [(path, chunk.label, chunk.text, np.asarray(vector, dtype=np.float32).tobytes())
            for chunk, vector in zip(chunks, embeddings)]
    with connection:
        connection.execute("DELETE FROM chunks WHERE path = ?", (path,))
        connection.executemany(
            "INSERT INTO chunks (path, label, text, embedding) VALUES (?, ?, ?, ?)", rows)


def delete_document(connection, path):
    with connection:
        connection.execute("DELETE FROM chunks WHERE path = ?", (path,))
        connection.execute("DELETE FROM documents WHERE path = ?", (path,))


def all_chunks(connection):
    rows = connection.execute("SELECT path, label, text, embedding FROM chunks ORDER BY id")
    return [StoredChunk(path, label, text, np.frombuffer(blob, dtype=np.float32))
            for path, label, text, blob in rows]


def document_state(connection):
    """Return {path: sha256} for every indexed document."""
    return dict(connection.execute("SELECT path, sha256 FROM documents"))
