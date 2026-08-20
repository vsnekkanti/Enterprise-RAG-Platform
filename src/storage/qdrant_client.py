from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

class QdrantService:
    def __init__(self, url="http://localhost:6333", api_key="qdrant_key"):
        self.client = QdrantClient(url=url, api_key=api_key, prefer_grpc=False)
        self.collection_name = "documents"

    def init_collection(self, vector_size: int = 384):
        try:
            self.client.get_collection(self.collection_name)
        except Exception:
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )

    def add_point(self, point_id: int, vector: list, payload: dict):
        point = PointStruct(id=point_id, vector=vector, payload=payload)
        self.client.upsert(collection_name=self.collection_name, points=[point])

    def search(self, vector: list, acl_groups: list, limit: int = 10):
        from qdrant_client.models import Filter, FieldCondition, MatchAny
        filter_cond = Filter(
            must=[FieldCondition(key="acl_groups", match=MatchAny(any=acl_groups))]
        )
        results = self.client.query_points(
            collection_name=self.collection_name,
            query=vector,
            query_filter=filter_cond,
            limit=limit
        )
        return results.points

    def retrieve_by_ids(self, point_ids: list, acl_groups: list) -> list:
        points = self.client.retrieve(
            collection_name=self.collection_name,
            ids=point_ids,
            with_payload=True
        )
        allowed = set(acl_groups)
        return [p for p in points if allowed & set(p.payload.get("acl_groups", []))]

    def get_stats(self) -> dict:
        collection = self.client.get_collection(self.collection_name)
        return {
            "points_count": collection.points_count
        }
