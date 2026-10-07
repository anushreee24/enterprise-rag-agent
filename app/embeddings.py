"""Step 3: embeddings = turning text into vectors so 'similar meaning' becomes
'nearby in space'. Two interchangeable backends behind one interface:

  * SentenceTransformerEmbedder - real semantic model (all-MiniLM-L6-v2, 384-d).
    Use this for the real thing.
  * HashingEmbedder - deterministic bag-of-words hashing. NOT semantic; it exists
    so the test-suite and CI run offline with no model download.
"""
import hashlib
import re
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    dim = 384

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            tokens = re.findall(r"[a-z0-9]+", text.lower())
            grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
            for g in grams:
                h = int(hashlib.md5(g.encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0 if (h >> 64) & 1 else -1.0
            norm = np.linalg.norm(vec)
            out.append((vec / norm if norm else vec).tolist())
        return out


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str):
        from sentence_transformers import SentenceTransformer  # lazy: heavy import
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


def get_embedder(backend: str, model_name: str) -> Embedder:
    if backend == "hash":
        return HashingEmbedder()
    if backend == "st":
        return SentenceTransformerEmbedder(model_name)
    raise ValueError(f"Unknown EMBEDDING_BACKEND: {backend}")
