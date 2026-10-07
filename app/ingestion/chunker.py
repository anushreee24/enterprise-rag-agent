"""Step 2: split text into overlapping chunks.

Why chunk? Embedding models work best on a few sentences, and the LLM context
window is limited. Why overlap? So a fact that straddles a boundary still lands
intact in at least one chunk.

Strategy: paragraph-aware greedy packing up to `size` characters; oversized
paragraphs fall back to sentence splitting, then a hard split."""
import re


def _split_long(paragraph: str, size: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", paragraph)
    out, cur = [], ""
    for s in sentences:
        while len(s) > size:                      # last resort: hard split
            if cur:
                out.append(cur)
                cur = ""
            out.append(s[:size])
            s = s[size:]
        if cur and len(cur) + len(s) + 1 > size:
            out.append(cur)
            cur = s
        else:
            cur = f"{cur} {s}".strip()
    if cur:
        out.append(cur)
    return out


def chunk_text(text: str, size: int = 900, overlap: int = 150) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[str] = []
    cur = ""
    for para in paragraphs:
        for piece in (_split_long(para, size) if len(para) > size else [para]):
            if cur and len(cur) + len(piece) + 2 > size:
                chunks.append(cur)
                tail = cur[-overlap:] if overlap else ""
                if " " in tail:                    # start overlap on a word boundary
                    tail = tail[tail.index(" ") + 1:]
                cur = f"{tail}\n\n{piece}".strip()
            else:
                cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        chunks.append(cur)
    return chunks
