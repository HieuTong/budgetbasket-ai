import re

from app.rag.knowledge_base import KNOWLEDGE_BASE


class Retriever:
    def __init__(self):
        self.docs = KNOWLEDGE_BASE

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict]:
        return self._keyword_fallback(
            query,
            top_k,
        )

    def _keyword_fallback(
        self,
        query: str,
        top_k: int,
    ) -> list[dict]:
        query_words = set(
            re.findall(
                r"\w+",
                query.lower(),
            )
        )

        scored = []

        for doc in self.docs:
            doc_words = set(
                re.findall(
                    r"\w+",
                    doc["text"].lower(),
                )
            )

            overlap = len(
                query_words & doc_words
            )

            scored.append(
                (overlap, doc)
            )

        scored.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [
            doc
            for _, doc in scored[:top_k]
        ]