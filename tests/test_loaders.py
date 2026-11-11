import docx
import pytest
from reportlab.pdfgen import canvas

from askfiles.loaders import SUPPORTED_EXTENSIONS, Segment, load_file


def test_supported_extensions():
    assert SUPPORTED_EXTENSIONS == {".pdf", ".docx", ".txt", ".md"}


@pytest.mark.parametrize("name", ["note.txt", "note.md", "NOTE.TXT"])
def test_text_files_are_one_utf8_segment(tmp_path, name):
    path = tmp_path / name
    path.write_text("Grüße aus Köln\nsecond line", encoding="utf-8")
    assert load_file(path) == [Segment(str(path), "", "Grüße aus Köln\nsecond line")]


def test_empty_text_file_gives_no_segments(tmp_path):
    path = tmp_path / "empty.txt"
    path.write_text("  \n", encoding="utf-8")
    assert load_file(path) == []


def test_pdf_gives_one_segment_per_page(tmp_path):
    path = tmp_path / "doc.pdf"
    pdf = canvas.Canvas(str(path))
    for text in ["alpha on the first page", "", "gamma on the third page"]:
        if text:
            pdf.drawString(72, 720, text)
        pdf.showPage()
    pdf.save()

    segments = load_file(path)

    # The empty second page is skipped, and the numbering still follows the PDF pages.
    assert [s.label for s in segments] == ["page 1", "page 3"]
    assert "alpha on the first page" in segments[0].text
    assert "gamma on the third page" in segments[1].text
    assert all(s.path == str(path) for s in segments)


def test_docx_gives_one_segment_per_heading(tmp_path):
    path = tmp_path / "doc.docx"
    document = docx.Document()
    document.add_paragraph("Intro before any heading.")
    document.add_heading("Budget", level=1)
    document.add_paragraph("The budget is 100.")
    document.add_paragraph("It was approved.")
    document.add_heading("Timeline", level=2)
    document.add_paragraph("Start in May.")
    document.add_heading("Empty section", level=1)
    document.save(str(path))

    assert load_file(path) == [
        Segment(str(path), "section (start)", "Intro before any heading."),
        Segment(str(path), "section Budget", "The budget is 100.\nIt was approved."),
        Segment(str(path), "section Timeline", "Start in May."),
    ]


def test_unsupported_extension_raises(tmp_path):
    path = tmp_path / "image.png"
    path.write_bytes(b"x")
    with pytest.raises(ValueError):
        load_file(path)
