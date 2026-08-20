import json
import hashlib
import redis
from typing import Optional, Any
import numpy as np

class SemanticCache:
    def __init__(self, threshold: float = 0.95):
        self.redis_client = redis.Redis(host="localhost", port=6379, decode_responses=True)
        self.threshold = threshold

    def cosine_similarity(self, vec1: list, vec2: list) -> float:
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2)))

    def get(self, embedding: list, user_id: int) -> Optional[dict]:
        key = f"cache:{user_id}:*"
        keys = self.redis_client.keys(key)
        for cached_key in keys:
            cached_data = self.redis_client.get(cached_key)
            if cached_data:
                cached = json.loads(cached_data)
                cached_embedding = cached.get("embedding")
                similarity = self.cosine_similarity(embedding, cached_embedding)
                if similarity >= self.threshold:
                    cached["hit"] = True
                    return cached
        return None

    def set(self, embedding: list, result: dict, user_id: int):
        hash_key = hashlib.md5(str(embedding[:10]).encode()).hexdigest()[:8]
        key = f"cache:{user_id}:{hash_key}"
        result["embedding"] = embedding
        result["hit"] = False
        self.redis_client.setex(key, 3600, json.dumps(result))

    def invalidate_user(self, user_id: int):
        key = f"cache:{user_id}:*"
        keys = self.redis_client.keys(key)
        for k in keys:
            self.redis_client.delete(k)
