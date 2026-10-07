"""FastAPI layer: HTTP endpoints, auth dependency, audit logging."""
import tempfile
from dataclasses import dataclass
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field

from . import rag
from .auth import create_token, decode_token
from .config import Settings, load_settings
from .embeddings import get_embedder
from .ingestion.pipeline import ingest_file
from .rbac import Role, chroma_filter, get_role
from .store import Store
from .vectorstore import VectorStore

STATIC = Path(__file__).resolve().parent.parent / "static"


class QueryIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    top_k: int | None = Field(default=None, ge=1, le=15)


@dataclass
class CurrentUser:
    username: str
    role: Role


def build_services(settings: Settings) -> tuple[VectorStore, Store]:
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    embedder = get_embedder(settings.embedding_backend, settings.embedding_model)
    return (VectorStore(settings.data_dir / "chroma", embedder), Store(settings.data_dir / "app.db"))


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    vectors, db = build_services(settings)
    app = FastAPI(title="Enterprise Document Intelligence RAG Agent", version="1.0.0")
    oauth2 = OAuth2PasswordBearer(tokenUrl="/auth/login")

    def current_user(token: str = Depends(oauth2)) -> CurrentUser:
        try:
            username = decode_token(token, settings.jwt_secret)
        except jwt.PyJWTError:
            raise HTTPException(401, "Invalid or expired token")
        role_name = db.get_role(username)           # role re-read from DB every request
        if not role_name:
            raise HTTPException(401, "Unknown user")
        return CurrentUser(username, get_role(role_name))

    @app.post("/auth/login")
    def login(form: OAuth2PasswordRequestForm = Depends()):
        role = db.verify_user(form.username, form.password)
        if not role:
            db.log(form.username, "-", "login_failed", {})
            raise HTTPException(401, "Incorrect username or password")
        db.log(form.username, role, "login", {})
        return {"access_token": create_token(form.username, settings.jwt_secret, settings.jwt_minutes),
                "token_type": "bearer", "role": role}

    @app.get("/me")
    def me(user: CurrentUser = Depends(current_user)):
        return {"username": user.username, "role": user.role.name}

    @app.post("/query")
    def query(body: QueryIn, user: CurrentUser = Depends(current_user)):
        result = rag.answer(settings, vectors, user.role, body.question, body.top_k)
        blocked = result.pop("_blocked")
        db.log(user.username, user.role.name, "query", {
            "question": body.question, "mode": result["mode"],
            "returned": [s["source"] for s in result["sources"]], "policy_mismatch_blocked": blocked})
        return result

    @app.get("/documents")
    def documents(user: CurrentUser = Depends(current_user)):
        """Lists only documents the caller is allowed to know exist."""
        return vectors.list_documents(chroma_filter(user.role))

    @app.post("/documents")
    async def upload(file: UploadFile = File(...), department: str = Form(...),
                     classification: str = Form(...), user: CurrentUser = Depends(current_user)):
        if not user.role.can_ingest:
            db.log(user.username, user.role.name, "ingest_denied", {"file": file.filename})
            raise HTTPException(403, "Your role cannot upload documents")
        safe_name = Path(file.filename or "upload").name
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / safe_name
            path.write_bytes(await file.read())
            try:
                info = ingest_file(vectors, path, department, classification,
                                   settings.chunk_size, settings.chunk_overlap)
            except ValueError as exc:
                raise HTTPException(400, str(exc))
        db.log(user.username, user.role.name, "ingest", info)
        return info

    @app.delete("/documents/{doc_id}")
    def delete_doc(doc_id: str, user: CurrentUser = Depends(current_user)):
        if not user.role.can_ingest:
            raise HTTPException(403, "Your role cannot delete documents")
        vectors.delete_document(doc_id)
        db.log(user.username, user.role.name, "delete", {"doc_id": doc_id})
        return {"deleted": doc_id}

    @app.get("/audit")
    def audit(limit: int = 50, user: CurrentUser = Depends(current_user)):
        if not user.role.can_view_audit:
            raise HTTPException(403, "Your role cannot view the audit log")
        return db.recent_audit(min(limit, 500))

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    app.state.vectors, app.state.db, app.state.settings = vectors, db, settings
    return app
