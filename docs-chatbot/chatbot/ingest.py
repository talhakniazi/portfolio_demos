"""Ingestion: read PDF, Word, Markdown, HTML and text files into clean, overlapping chunks with their source."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

import pdfplumber
from bs4 import BeautifulSoup, Comment
from docx import Document

SUPPORTED = {".pdf", ".docx", ".md", ".txt", ".html", ".htm"}


@dataclass
class Chunk:
    id: str
    source: str          # file name
    location: str        # page number or section heading, shown in citations
    text: str


def _sections_from_lines(lines, items=False):
    """Group lines under the most recent heading-like line."""
    heading, buf = "", []
    for kind, text in lines:
        if kind == "h":
            if buf:
                yield heading, " ".join(buf)
            heading, buf = text, []
        elif text:
            buf.append(text + "." if items and text[-1] not in ".!?:;" else text)   # list items become sentences; wrapped PDF lines don't
    if buf:
        yield heading, " ".join(buf)


def read_pdf(path):
    with pdfplumber.open(path) as pdf:
        for n, page in enumerate(pdf.pages, 1):
            words = page.extract_words(extra_attrs=["size", "fontname"])
            if not words:
                continue
            body = sorted({round(w["size"]) for w in words}, key=lambda s: -sum(1 for w in words if round(w["size"]) == s))[0]
            lines, cur, top = [], [], None
            for w in words:                      # rebuild lines, marking larger/bold text as headings
                if top is not None and abs(w["top"] - top) > 3:
                    lines.append(cur); cur = []
                cur.append(w); top = w["top"]
            lines.append(cur)
            out = []
            for ln in lines:
                text = " ".join(w["text"] for w in ln)
                is_h = round(ln[0]["size"]) > body or ("Bold" in ln[0]["fontname"] and len(text) < 80)
                out.append(("h" if is_h else "p", text))
            for heading, text in _sections_from_lines(out):
                yield f"page {n}" + (f", {heading}" if heading else ""), text


def read_docx(path):
    lines = [("h" if p.style.name.lower().startswith(("heading", "title")) else "p", p.text.strip()) for p in Document(path).paragraphs]
    for t in Document(path).tables:
        for row in t.rows:
            lines.append(("p", " | ".join(c.text.strip() for c in row.cells)))
    yield from _sections_from_lines(lines, items=True)


def read_markdown(path):
    lines = []
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        s = raw.strip()
        if s.startswith("#"):
            lines.append(("h", s.lstrip("#").strip()))
        else:
            lines.append(("p", re.sub(r"^[-*]\s+|[*_`]", "", s)))
    yield from _sections_from_lines(lines, items=True)


def read_html(path):
    soup = BeautifulSoup(Path(path).read_text(encoding="utf-8"), "html.parser")
    for c in soup.find_all(string=lambda s: isinstance(s, Comment)):
        c.extract()                              # hidden comments are not content (and are a prompt-injection route)
    for t in soup(["script", "style", "nav", "footer", "header", "form", "noscript"]):
        t.decompose()
    root = soup.find("main") or soup.body or soup
    lines = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if txt:
            lines.append(("h" if el.name.startswith("h") else "p", txt))
    yield from _sections_from_lines(lines, items=True)


READERS = {".pdf": read_pdf, ".docx": read_docx, ".md": read_markdown, ".txt": read_markdown, ".html": read_html, ".htm": read_html}


def split(text: str, max_words=120, overlap=25):
    """Split long sections on sentence boundaries, keeping a little overlap so answers aren't cut in half."""
    sents = re.split(r"(?<=[.!?])\s+", text.strip())
    chunk, out = [], []
    for s in sents:
        if chunk and len(" ".join(chunk + [s]).split()) > max_words:
            out.append(" ".join(chunk))
            tail = " ".join(chunk).split()[-overlap:]
            chunk = [" ".join(tail)]
        chunk.append(s)
    if chunk:
        out.append(" ".join(chunk))
    return out


def ingest(folder: Path) -> list[Chunk]:
    chunks = []
    for path in sorted(Path(folder).iterdir()):
        if path.suffix.lower() not in SUPPORTED:
            continue
        for location, text in READERS[path.suffix.lower()](path):
            if "fictional company created for a portfolio" in text.lower() and len(text.split()) < 14:
                continue                          # skip the demo disclaimer line itself
            for part in split(text):
                h = hashlib.sha1(f"{path.name}|{location}|{part}".encode()).hexdigest()[:12]
                chunks.append(Chunk(h, path.name, location, part))
    return chunks


def save(chunks: list[Chunk], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([asdict(c) for c in chunks], indent=1), encoding="utf-8")


def load(path: Path) -> list[Chunk]:
    return [Chunk(**d) for d in json.loads(Path(path).read_text(encoding="utf-8"))]
