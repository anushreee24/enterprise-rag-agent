"""Create demo users and ingest the sample documents.   python -m scripts.seed"""
import json
from pathlib import Path

from app.config import load_settings
from app.ingestion.pipeline import ingest_file
from app.main import build_services

DEMO_USERS = [("alice", "employee"), ("hannah", "hr_manager"), ("frank", "finance_analyst"),
              ("carl", "compliance_officer"), ("root", "admin")]
DEMO_PASSWORD = "Passw0rd!"          # demo only - never reuse in a real deployment


def seed(settings=None, docs_dir: Path = Path("sample_docs")) -> None:
    settings = settings or load_settings()
    vectors, db = build_services(settings)
    for username, role in DEMO_USERS:
        db.create_user(username, DEMO_PASSWORD, role)
    for item in json.loads((docs_dir / "manifest.json").read_text()):
        info = ingest_file(vectors, docs_dir / item["file"], item["department"], item["classification"],
                           settings.chunk_size, settings.chunk_overlap)
        print(f"ingested {info['source']:<34} {info['classification']:<13} {info['department']:<12} {info['chunks']} chunk(s)")
    print(f"\nDemo users (password '{DEMO_PASSWORD}'): " + ", ".join(f"{u}={r}" for u, r in DEMO_USERS))


if __name__ == "__main__":
    seed()
