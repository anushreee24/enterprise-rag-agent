import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("EMBEDDING_BACKEND", "hash")      # offline, deterministic
    monkeypatch.setenv("MIN_SCORE", "0.05")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("JWT_SECRET", "test-secret")


@pytest.fixture()
def client(env):
    from app.config import load_settings
    from app.main import create_app
    from scripts.seed import seed
    settings = load_settings()
    seed(settings, ROOT / "sample_docs")
    return TestClient(create_app(settings))


def login(client, user, password="Passw0rd!"):
    r = client.post("/auth/login", data={"username": user, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
