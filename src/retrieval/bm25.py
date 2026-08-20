from rank_bm25 import BM25Okapi
from typing import List, Tuple

class BM25Search:
    def __init__(self):
        self.bm25 = None
        self.corpus = []

    def index(self, documents: List[str]):
        tokenized = [doc.lower().split() for doc in documents]
        self.bm25 = BM25Okapi(tokenized)
        self.corpus = documents

    def search(self, query: str, limit: int = 10) -> List[Tuple[int, float]]:
        if not self.bm25:
            return []
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        return ranked[:limit]
