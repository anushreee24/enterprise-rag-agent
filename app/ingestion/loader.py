"""Step 1 of ingestion: turn a file on disk into plain text, page by page.
Page numbers are kept so answers can cite 'file.pdf, p.3'."""
from pathlib import Path

from pypdf import PdfReader


def load_document(path: Path) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(path))
        pages = [(i + 1, (p.extract_text() or "").strip()) for i, p in enumerate(reader.pages)]
        return [(n, t) for n, t in pages if t]
    if suffix in {".txt", ".md"}:
        return [(1, path.read_text(encoding="utf-8", errors="ignore").strip())]
    raise ValueError(f"Unsupported file type: {suffix} (use .pdf, .txt or .md)")
