"""
FAISS-backed retriever with a keyword-overlap fallback so the whole
pipeline still works (and is demoable) without an API key -- worth
mentioning in an interview as a resilience/cost-control decision.
"""
import re

import numpy as np

from app.core.config import settings
from app.rag.knowledge_base import KNOWLEDGE_BASE

try:
    import faiss
    from openai import OpenAI

    _HAS_FAISS = True
except ImportError:
    _HAS_FAISS = False


class Retriever:
    def __init__(self):
        self.docs = KNOWLEDGE_BASE
        self._index = None
        self._client = None

        if _HAS_FAISS and settings.OPENAI_API_KEY:
            self._client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self._build_index()

    def _embed(self, texts: list[str]) -> np.ndarray:
        resp = self._client.embeddings.create(model=settings.EMBEDDING_MODEL, input=texts)
        return np.array([d.embedding for d in resp.data], dtype="float32")

    def _build_index(self):
        vectors = self._embed([d["text"] for d in self.docs])
        dim = vectors.shape[1]
        self._index = faiss.IndexFlatL2(dim)
        self._index.add(vectors)

    def retrieve(self, query: str, top_k: int = 3) -> list[dict]:
        if self._index is not None:
            q_vec = self._embed([query])
            distances, indices = self._index.search(q_vec, top_k)
            return [self.docs[i] for i in indices[0] if i < len(self.docs)]
        return self._keyword_fallback(query, top_k)

    def _keyword_fallback(self, query: str, top_k: int) -> list[dict]:
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for doc in self.docs:
            doc_words = set(re.findall(r"\w+", doc["text"].lower()))
            overlap = len(query_words & doc_words)
            scored.append((overlap, doc))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [doc for _, doc in scored[:top_k]]
