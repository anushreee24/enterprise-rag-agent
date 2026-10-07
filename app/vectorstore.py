"""Step 4: the vector database (ChromaDB, persisted to disk).

Each chunk is stored with: its text, its embedding, and METADATA - department,
classification and classification_level. That metadata is what makes
policy-enforced retrieval possible: the access filter runs *inside* the
nearest-neighbour search."""
from pathlib import Path

import chromadb

from .embeddings import Embedder

COLLECTION = "enterprise_docs"


class VectorStore:
    def __init__(self, path: Path, embedder: Embedder):
        self.embedder = embedder
        self.client = chromadb.PersistentClient(path=str(path))
        # cosine distance pairs with normalised embeddings; we pass our own
        # embeddings, so Chroma's built-in embedding function is not used.
        self.col = self.client.get_or_create_collection(
            COLLECTION, metadata={"hnsw:space": "cosine"})

    def upsert(self, ids: list[str], texts: list[str], metas: list[dict]) -> None:
        # upsert (not add) -> re-ingesting the same file is idempotent
        self.col.upsert(ids=ids, documents=texts, metadatas=metas,
                        embeddings=self.embedder.embed(texts))

    def search(self, query: str, where: dict, k: int) -> list[dict]:
        if self.col.count() == 0:
            return []
        res = self.col.query(
            query_embeddings=self.embedder.embed([query]),
            n_results=min(k, self.col.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for text, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({"text": text, "meta": meta, "score": round(1.0 - float(dist), 4)})
        return hits

    def list_documents(self, where: dict) -> list[dict]:
        res = self.col.get(where=where, include=["metadatas"])
        docs: dict[str, dict] = {}
        for m in res["metadatas"]:
            d = docs.setdefault(m["doc_id"], {
                "doc_id": m["doc_id"], "source": m["source"], "department": m["department"],
                "classification": m["classification"], "chunks": 0})
            d["chunks"] += 1
        return sorted(docs.values(), key=lambda d: d["source"])

    def delete_document(self, doc_id: str) -> None:
        self.col.delete(where={"doc_id": doc_id})
