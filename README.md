# Enterprise Document Intelligence & Semantic RAG Knowledge Agent

Ask natural-language questions over internal documents (PDF / TXT / MD) and get **cited answers** -
while **role-based access control** guarantees each user can only retrieve what their role permits.

## Architecture

```
 PDF/TXT/MD ──► loader ──► chunker ──► embedder ──► ChromaDB (vectors + metadata)
                (pypdf)   (overlap)  (MiniLM-L6)     metadata: department, classification
                                                              ▲
 user ─► /auth/login ─► JWT ─► /query ─► role lookup ─► policy filter (WHERE clause) ─┘
                                           │                    │
                                           │                    ▼
                                           │          top-k allowed chunks ─► re-check can_access()
                                           ▼                                         │
                                      audit log (SQLite)            Claude (cited answer) / extractive fallback
```

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set JWT_SECRET; optionally ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
python -m scripts.seed          # demo users + 7 sample documents
uvicorn app.server:app --reload # open http://localhost:8000  (API docs: /docs)
```

Demo users (password `Passw0rd!`): `alice` employee · `hannah` hr_manager · `frank` finance_analyst ·
`carl` compliance_officer · `root` admin.  Try *"What are the salary bands?"* as alice, then as hannah.

Offline / CI run (no model download): `EMBEDDING_BACKEND=hash`. Tests: `pip install -r requirements-dev.txt && pytest`.

## Access-control model

| Role | Max classification | Departments |
|---|---|---|
| employee | internal | general |
| hr_manager | confidential | general, hr |
| finance_analyst | confidential | general, finance |
| compliance_officer | restricted | general, compliance, legal, it_security |
| admin | restricted | all (+ can ingest/delete) |

Enforced in **two layers**: (1) a metadata `where` filter inside the vector search, so forbidden chunks are never
retrieved; (2) a Python `can_access()` re-check on every returned chunk. A test asserts both layers always agree.

## API

| Endpoint | Who | Purpose |
|---|---|---|
| `POST /auth/login` | anyone | get JWT |
| `POST /query` | any user | ask a question -> answer + citations |
| `GET /documents` | any user | list documents *you* may see |
| `POST /documents` | admin | upload + tag (department, classification) |
| `DELETE /documents/{id}` | admin | remove a document |
| `GET /audit` | compliance, admin | who asked what, what was returned |

## Known limitations (be upfront about these)

- Demo auth is local users + JWT. Production = SSO/OIDC (Okta, Entra ID) mapping groups -> roles.
- Scanned PDFs need an OCR step (e.g. Tesseract / Azure Document Intelligence); not included.
- One document = one classification. Per-page or per-section ACLs would need finer metadata.
- No reranker or hybrid (BM25 + vector) search yet; both are the natural next accuracy upgrades.
- Chroma is single-node. For multi-tenant scale, swap `vectorstore.py` for Pinecone / pgvector / Azure AI Search
  (the class is the only file that touches the DB).
