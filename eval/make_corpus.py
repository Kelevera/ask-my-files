"""Generate the synthetic eval corpus and its questions. Deterministic (seed 42).

Run: python -m eval.make_corpus
"""
import io
import json
import random
import shutil
import textwrap
import zipfile
from pathlib import Path

import docx
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

EVAL_DIR = Path(__file__).resolve().parent
DATA_DIR = EVAL_DIR / "data"
QUESTIONS_PATH = EVAL_DIR / "questions.json"

SEED = 42
ANSWERABLE = 30
UNANSWERABLE = 10

ADJECTIVES = ["Amber", "Brisk", "Cobalt", "Dusty", "Ember", "Frosty", "Golden", "Hollow",
              "Ivory", "Jade", "Crimson", "Lunar"]
NOUNS = ["Falcon", "Harbor", "Lantern", "Meadow", "Nimbus", "Orchid", "Pioneer", "Quartz",
         "Raven", "Summit", "Tundra", "Voyager"]
TEAMS = ["finance", "logistics", "support", "design", "quality", "legal", "sales", "platform"]
THINGS = ["quarterly forecast", "vendor contract", "release checklist", "training plan",
          "office move", "audit findings", "customer survey", "backup schedule",
          "travel policy", "hiring roadmap"]
VERBS = ["reviewed", "approved", "postponed", "revised", "discussed", "archived"]
PERIODS = ["Monday", "last week", "the spring", "the third quarter", "the offsite", "January"]
REMARKS = ["No further action is required.", "A follow-up meeting is planned.",
           "The notes were shared with all members.", "Two open points remain.",
           "The decision was unanimous.", "Details are in the appendix."]
HEADINGS = ["Overview", "Budget", "Timeline", "Risks", "Contacts", "Staffing", "Next Steps"]
FOLDERS = ["", "reports", "notes/archive"]
# (extension, list of page counts; 0 = not a PDF)
LAYOUT = [(".pdf", [4, 3, 5, 3, 1, 2, 2, 1]), (".docx", [0] * 6), (".txt", [0] * 6),
          (".md", [0] * 5)]


def _sentence(rng):
    return (f"The {rng.choice(TEAMS)} team {rng.choice(VERBS)} the {rng.choice(THINGS)} "
            f"during {rng.choice(PERIODS)}. {rng.choice(REMARKS)}")


def _paragraphs(rng, facts):
    """Filler paragraphs with the given fact sentences inserted as their own paragraphs."""
    paragraphs = [" ".join(_sentence(rng) for _ in range(rng.randint(2, 3)))
                  for _ in range(rng.randint(3, 4))]
    for fact in facts:
        paragraphs.insert(rng.randint(0, len(paragraphs)), fact)
    return paragraphs


def _write_text(path, parts):
    blocks = []
    for heading, paragraphs in parts:
        blocks += [heading] + paragraphs
    path.write_bytes("\n\n".join(blocks).encode("utf-8") + b"\n")


def _write_md(path, parts):
    blocks = [f"# {path.stem}"]
    for heading, paragraphs in parts:
        blocks += [f"## {heading}"] + paragraphs
    path.write_bytes("\n\n".join(blocks).encode("utf-8") + b"\n")


def _write_pdf(path, parts):
    pdf = canvas.Canvas(str(path), pagesize=A4, invariant=1)
    for _, paragraphs in parts:
        pdf.setFont("Helvetica", 10)
        y = 800
        for paragraph in paragraphs:
            for line in textwrap.wrap(paragraph, 95):
                pdf.drawString(50, y, line)
                y -= 14
            y -= 10
        pdf.showPage()
    pdf.save()


def _write_docx(path, parts):
    document = docx.Document()
    for heading, paragraphs in parts:
        document.add_heading(heading, level=1)
        for paragraph in paragraphs:
            document.add_paragraph(paragraph)
    buffer = io.BytesIO()
    document.save(buffer)
    # python-docx stamps the zip entries with the current time. Rewrite them with a fixed
    # time so that two runs are byte-identical.
    with zipfile.ZipFile(buffer) as source, zipfile.ZipFile(path, "w") as target:
        for name in source.namelist():
            info = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            target.writestr(info, source.read(name))


WRITERS = {".txt": _write_text, ".md": _write_md, ".pdf": _write_pdf, ".docx": _write_docx}


def generate(data_dir=DATA_DIR, questions_path=QUESTIONS_PATH):
    """Write 25 documents into data_dir and 40 questions into questions_path."""
    rng = random.Random(SEED)
    data_dir = Path(data_dir)
    if data_dir.exists():
        shutil.rmtree(data_dir)

    names = [f"{a} {n}" for a in ADJECTIVES for n in NOUNS]
    rng.shuffle(names)
    facts = []  # (name, code, relative file, label)
    number = 0
    for extension, page_counts in LAYOUT:
        for pages in page_counts:
            number += 1
            folder = FOLDERS[number % len(FOLDERS)]
            relative = f"{folder}/doc{number:02d}{extension}".lstrip("/")
            if extension == ".pdf":
                headings = [f"page {page}" for page in range(1, pages + 1)]
            else:
                headings = rng.sample(HEADINGS, 4)
            planted = {heading: [] for heading in headings}
            for _ in range(rng.randint(2, 3)):
                name = names.pop()
                code = ("".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZ") for _ in range(3))
                        + "-" + "".join(rng.choice("0123456789") for _ in range(4)))
                heading = rng.choice(headings)
                planted[heading].append(f"The access code for Project {name} is {code}.")
                label = {".pdf": heading, ".docx": f"section {heading}"}.get(extension, "")
                facts.append((name, code, relative, label))
            parts = [(heading, _paragraphs(rng, planted[heading])) for heading in headings]
            path = data_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            WRITERS[extension](path, parts)

    questions = []
    for name, code, relative, label in rng.sample(facts, ANSWERABLE):
        questions.append({"question": f"What is the access code for Project {name}?",
                          "answerable": True, "expected_code": code,
                          "expected_file": relative, "expected_label": label})
    for name in names[:UNANSWERABLE]:  # names that were never planted
        questions.append({"question": f"What is the access code for Project {name}?",
                          "answerable": False, "expected_code": None,
                          "expected_file": None, "expected_label": None})
    for index, question in enumerate(questions, start=1):
        question["id"] = f"Q{index:02d}"
    Path(questions_path).write_bytes(json.dumps(questions, indent=2).encode("utf-8") + b"\n")
    return questions


if __name__ == "__main__":
    generate()
    print(f"Wrote 25 documents to {DATA_DIR} and 40 questions to {QUESTIONS_PATH}")
