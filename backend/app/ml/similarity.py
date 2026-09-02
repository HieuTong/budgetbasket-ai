"""
Item-item similarity for 'similar to what you usually buy'.

MVP uses TF-IDF over product name+category+tags, which is fast, needs
no external API, and is a defensible engineering choice to explain in
an interview (no embedding cost/latency for a feature this simple).
Swap in sentence-transformers embeddings later without changing the
public interface (recommend_similar).
"""
from dataclasses import dataclass

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Product:
    id: int
    name: str
    category: str
    unit_price: float
    nutrition_tags: str = ""

    def text(self) -> str:
        return f"{self.name} {self.category} {self.nutrition_tags}"


class SimilarityIndex:
    def __init__(self, products: list[Product]):
        self.products = products
        self._vectorizer = TfidfVectorizer(stop_words="english")
        self._matrix = self._vectorizer.fit_transform([p.text() for p in products])

    def recommend_similar(self, product_id: int, top_k: int = 5) -> list[tuple[Product, float]]:
        idx = next(i for i, p in enumerate(self.products) if p.id == product_id)
        sims = cosine_similarity(self._matrix[idx], self._matrix).flatten()
        ranked = np.argsort(-sims)
        results = []
        for i in ranked:
            if i == idx:
                continue
            results.append((self.products[i], float(sims[i])))
            if len(results) >= top_k:
                break
        return results

    def cheaper_substitutes(self, product_id: int, top_k: int = 3) -> list[tuple[Product, float]]:
        """Similar items, filtered to strictly cheaper ones, ranked by
        a blend of similarity and savings."""
        base = next(p for p in self.products if p.id == product_id)
        candidates = self.recommend_similar(product_id, top_k=20)
        cheaper = [(p, sim) for p, sim in candidates if p.unit_price < base.unit_price]
        cheaper.sort(key=lambda t: t[1] - 0.01 * (base.unit_price - t[0].unit_price), reverse=True)
        return cheaper[:top_k]
