from app.ingestion.chunker import chunk_text


def test_chunks_respect_size_and_cover_text():
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 60 for i in range(10))
    chunks = chunk_text(text, size=500, overlap=80)
    assert len(chunks) > 1
    assert all(len(c) <= 500 + 80 + 10 for c in chunks)       # size + overlap tail
    assert "Paragraph 0" in chunks[0] and "Paragraph 9" in chunks[-1]


def test_oversized_single_paragraph_is_split():
    chunks = chunk_text("x" * 2500, size=1000, overlap=0)
    assert len(chunks) == 3
