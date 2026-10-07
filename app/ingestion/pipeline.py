"""Glue: file -> pages -> chunks -> metadata-tagged vectors in ChromaDB."""
import hashlib
from pathlib import Path

from ..rbac import CLASSIFICATION, DEPARTMENTS
from ..vectorstore import VectorStore
from .chunker import chunk_text
from .loader import load_document


def ingest_file(store: VectorStore, path: Path, department: str, classification: str,
                chunk_size: int = 900, chunk_overlap: int = 150) -> dict:
    if department not in DEPARTMENTS:
        raise ValueError(f"department must be one of {DEPARTMENTS}")
    if classification not in CLASSIFICATION:
        raise ValueError(f"classification must be one of {list(CLASSIFICATION)}")

    pages = load_document(path)
    if not pages:
        raise ValueError("No extractable text found (scanned PDF? add an OCR step)")

    # Stable id from file content -> same file = same doc_id = idempotent upsert
    digest = hashlib.sha256("".join(t for _, t in pages).encode()).hexdigest()[:12]
    ids, texts, metas = [], [], []
    for page_no, page_text in pages:
        for i, chunk in enumerate(chunk_text(page_text, chunk_size, chunk_overlap)):
            ids.append(f"{digest}-p{page_no}-{i}")
            texts.append(chunk)
            metas.append({
                "doc_id": digest, "source": path.name, "page": page_no,
                "department": department, "classification": classification,
                "classification_level": CLASSIFICATION[classification],
            })
    store.upsert(ids, texts, metas)
    return {"doc_id": digest, "source": path.name, "chunks": len(ids),
            "department": department, "classification": classification}
