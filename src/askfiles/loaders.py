"""Read documents into segments. A segment is one page, one section or one whole file."""
from dataclasses import dataclass
from pathlib import Path

import docx
import pypdf

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}


@dataclass(frozen=True)
class Segment:
    path: str
    label: str
    text: str


def _load_text(path):
    return [("", Path(path).read_text(encoding="utf-8"))]


def _load_pdf(path):
    reader = pypdf.PdfReader(str(path))
    return [(f"page {number}", page.extract_text() or "")
            for number, page in enumerate(reader.pages, start=1)]


def _load_docx(path):
    sections = [("section (start)", [])]
    for paragraph in docx.Document(str(path)).paragraphs:
        if paragraph.style.name.startswith("Heading"):
            sections.append((f"section {paragraph.text.strip()}", []))
        else:
            sections[-1][1].append(paragraph.text)
    return [(label, "\n".join(lines)) for label, lines in sections]


_LOADERS = {".txt": _load_text, ".md": _load_text, ".pdf": _load_pdf, ".docx": _load_docx}


def load_file(path):
    """Return the non-empty segments of a file, in document order."""
    loader = _LOADERS.get(Path(path).suffix.lower())
    if loader is None:
        raise ValueError(f"Unsupported file type: {path}")
    return [Segment(str(path), label, text.strip())
            for label, text in loader(path) if text.strip()]
