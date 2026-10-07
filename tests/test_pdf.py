import pytest

pytest.importorskip("reportlab")


def test_pdf_ingest_keeps_page_numbers(env, tmp_path):
    from reportlab.pdfgen import canvas
    from app.config import load_settings
    from app.ingestion.pipeline import ingest_file
    from app.main import build_services

    pdf = tmp_path / "policy.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 750, "Page one covers travel reimbursement rules for employees.")
    c.showPage()
    c.drawString(72, 750, "Page two covers the expense approval workflow for managers.")
    c.save()

    s = load_settings()
    vectors, _ = build_services(s)
    info = ingest_file(vectors, pdf, "general", "internal")
    assert info["chunks"] == 2
    pages = {m["page"] for m in vectors.col.get(include=["metadatas"])["metadatas"]}
    assert pages == {1, 2}
