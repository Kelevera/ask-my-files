"""Answer a question from the indexed documents, with citations, or refuse."""
import os
import re
from dataclasses import dataclass

from . import config
from .retriever import top_k

NOT_IN_DOCUMENTS = "NOT_IN_DOCUMENTS"
REFUSAL_MESSAGE = "I cannot find the answer in your documents."
SYSTEM_PROMPT = (
    "You answer questions about the user's documents.\n"
    "Rules:\n"
    "1. Answer only from the numbered sources in the user message. Do not use other knowledge.\n"
    "2. Cite every source you use as [n], where n is the source number.\n"
    "3. If the answer is not in the sources, reply exactly NOT_IN_DOCUMENTS and nothing else.\n"
    "4. Keep the answer short and copy names, numbers and codes exactly as written."
)


@dataclass(frozen=True)
class Citation:
    path: str
    label: str


@dataclass(frozen=True)
class Answer:
    answer: str
    refused: bool
    citations: list  # Citation objects, in the order the answer cites them
    scores: list     # similarity score of each retrieved source, highest first
    sources: list    # the retrieved chunks, same order as scores


def describe(path, label):
    """Format a source as "file, page N" or "file, section X" (file name only)."""
    name = os.path.basename(path)
    return f"{name}, {label}" if label else name


def build_prompt(question, chunks):
    blocks = [f"[{number}] ({describe(chunk.path, chunk.label)})\n{chunk.text}"
              for number, chunk in enumerate(chunks, start=1)]
    return "Sources:\n\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}"


def _citations(reply, chunks):
    numbers = [int(n) for n in re.findall(r"\[(\d+)\]", reply)]
    cited = [chunks[n - 1] for n in numbers if 1 <= n <= len(chunks)] or chunks[:2]
    return list(dict.fromkeys(Citation(chunk.path, chunk.label) for chunk in cited))


def answer(connection, embed, chat, question, k=5, min_score=None):
    """embed: list of strings -> vectors. chat: (system, user) -> reply text."""
    if min_score is None:
        min_score = config.load().min_score
    results = top_k(connection, embed, question, k)
    chunks = [chunk for chunk, _ in results]
    scores = [score for _, score in results]

    def refusal():
        return Answer(REFUSAL_MESSAGE, True, [], scores, chunks)

    if not results or scores[0] < min_score:
        return refusal()
    reply = chat(SYSTEM_PROMPT, build_prompt(question, chunks)).strip()
    if NOT_IN_DOCUMENTS in reply:
        return refusal()
    return Answer(reply, False, _citations(reply, chunks), scores, chunks)
