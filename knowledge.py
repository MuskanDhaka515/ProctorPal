"""Retrieval over the testing-center policy FAQ (TF-IDF, no external API needed)."""
import os
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

FAQ_PATH = os.path.join(os.path.dirname(__file__), "data", "faq.md")


class PolicyKnowledgeBase:
    def __init__(self, path: str = FAQ_PATH):
        with open(path, encoding="utf-8") as f:
            text = f.read()
        # Each "## Heading" section is one retrievable chunk.
        parts = re.split(r"^## ", text, flags=re.MULTILINE)[1:]
        self.chunks = []
        for part in parts:
            title, _, body = part.partition("\n")
            self.chunks.append({"title": title.strip(), "text": body.strip()})
        corpus = [f"{c['title']} {c['text']}" for c in self.chunks]
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(corpus)

    def search(self, query: str, k: int = 2, min_score: float = 0.05) -> list[dict]:
        scores = cosine_similarity(self.vectorizer.transform([query]), self.matrix)[0]
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:k]
        return [
            {**self.chunks[i], "score": round(float(s), 3)}
            for i, s in ranked
            if s >= min_score
        ]


_kb = None


def get_kb() -> PolicyKnowledgeBase:
    global _kb
    if _kb is None:
        _kb = PolicyKnowledgeBase()
    return _kb
