from typing import List, Tuple, Optional
from src.storage.qdrant_client import QdrantService

class VectorSearch:
    def __init__(self, qdrant: QdrantService):
        self.qdrant = qdrant

    def search(
        self,
        query_vector: List[float],
        acl_groups: List[str],
        limit: int = 10,
    ) -> List[Tuple[int, float]]:
        if not acl_groups:
            raise ValueError("acl_groups parameter is required for RBAC")
        results = self.qdrant.search(query_vector, acl_groups, limit=limit)
        scored = []
        for i, point in enumerate(results):
            scored.append((point.id, float(point.score)))
        return scored
