"""Rank stored chunks by cosine similarity to a query."""
import numpy as np

from . import store


def top_k(connection, embed, query, k=5):
    """Return the k best (chunk, score) pairs for the query, highest score first.

    embed is a function: list of strings -> list of vectors.
    """
    chunks = store.all_chunks(connection)
    if not chunks:
        return []
    matrix = np.stack([chunk.embedding for chunk in chunks]).astype(np.float64)
    vector = np.asarray(embed([query])[0], dtype=np.float64)
    norms = np.linalg.norm(matrix, axis=1) * np.linalg.norm(vector)
    norms[norms == 0] = 1.0  # a zero vector has a dot product of 0, so its score is 0
    scores = matrix @ vector / norms
    order = np.argsort(-scores, kind="stable")[:k]
    return [(chunks[i], float(scores[i])) for i in order]
