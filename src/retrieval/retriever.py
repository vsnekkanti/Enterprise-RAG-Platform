from typing import List, Dict, Any
from .bm25 import BM25Search
from .vector_search import VectorSearch
from .rrf import RRF
from .reranker import CrossEncoderReranker
from src.storage.qdrant_client import QdrantService
from src.ingestion.embeddings import EmbeddingService

class HybridRetriever:
    def __init__(self):
        self.qdrant = QdrantService()
        self.vector_search = VectorSearch(self.qdrant)
        self.embedder = EmbeddingService()
        self.rrf = RRF(k=60)
        self.reranker = CrossEncoderReranker()
        self.corpus = {}

    def _build_corpus_from_qdrant(self, acl_groups: List[str]) -> dict:
        key = tuple(sorted(acl_groups))
        if key not in self.corpus:
            results = self.qdrant.search([0.0] * 384, acl_groups, limit=1000)
            ids = [point.id for point in results]
            texts = [point.payload.get("text", "") for point in results]
            bm25 = BM25Search()
            bm25.index(texts)
            self.corpus[key] = {
                "bm25": bm25,
                "text_by_id": dict(zip(ids, texts)),
            }
        return self.corpus[key]

    def retrieve(
        self,
        query: str,
        acl_groups: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        if not acl_groups:
            raise ValueError("acl_groups required for RBAC")
        corpus = self._build_corpus_from_qdrant(acl_groups)
        fetch_k = max(limit * 4, 20)

        query_vector = self.embedder.embed_single(query)
        bm25_hits = corpus["bm25"].search(query, limit=fetch_k)
        corpus_ids = list(corpus["text_by_id"].keys())
        bm25_results = [
            (corpus_ids[idx], score) for idx, score in bm25_hits
            if idx < len(corpus_ids)
        ]
        vector_results = self.vector_search.search(
            query_vector, acl_groups, limit=fetch_k
        )

        fused = self.rrf.fuse(bm25_results, vector_results)
        candidates = [
            {"id": doc_id, "text": corpus["text_by_id"].get(doc_id, "")}
            for doc_id, _ in fused[:fetch_k]
        ]
        return self.reranker.rerank(query, candidates, top_k=limit)
