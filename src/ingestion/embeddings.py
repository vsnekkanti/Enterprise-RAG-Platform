import numpy as np
from typing import List

class EmbeddingService:
    def __init__(self, model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.vector_size = 384
        except ImportError:
            raise ImportError("sentence-transformers not installed")

    def embed(self, texts: List[str]) -> np.ndarray:
        return self.model.encode(texts, show_progress_bar=False)

    def embed_single(self, text: str) -> list:
        return self.model.encode(text, show_progress_bar=False).tolist()
