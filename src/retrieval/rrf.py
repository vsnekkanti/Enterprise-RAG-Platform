from typing import List, Dict, Tuple

class RRF:
    def __init__(self, k: int = 60):
        self.k = k

    def fuse(
        self,
        *ranker_results: List[Tuple[int, float]]
    ) -> List[Tuple[int, float]]:
        scores: Dict[int, float] = {}
        for ranker in ranker_results:
            for rank, (doc_id, _) in enumerate(ranker):
                rrf_score = 1.0 / (self.k + rank + 1)
                if doc_id not in scores:
                    scores[doc_id] = 0.0
                scores[doc_id] += rrf_score
        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return ranked

    def compute_score(self, rank: int) -> float:
        return 1.0 / (self.k + rank + 1)
