import pytest
from src.retrieval.bm25 import BM25Search
from src.retrieval.vector_search import VectorSearch
from src.retrieval.rrf import RRF
from src.retrieval.retriever import HybridRetriever
from src.storage.qdrant_client import QdrantService

def test_bm25_exact_match():
    bm25 = BM25Search()
    docs = [
        "Figure 3.1: The Transformer architecture",
        "Figure 3.2: Multi-head attention mechanism",
        "Figure 2.1: LSTM recurrent neural network",
    ]
    bm25.index(docs)
    results = bm25.search("Figure 3.1", limit=3)
    assert len(results) > 0
    assert results[0][0] == 0

def test_vector_search_requires_acl_groups():
    qdrant = QdrantService()
    vs = VectorSearch(qdrant)
    with pytest.raises(ValueError, match="acl_groups parameter is required"):
        vs.search([0.1] * 384, [], limit=10)

def test_rrf_fusion_unit():
    rrf = RRF(k=60)
    ranker1 = [(1, 0.9), (2, 0.7), (3, 0.5)]
    ranker2 = [(3, 0.8), (1, 0.6), (4, 0.4)]
    fused = rrf.fuse(ranker1, ranker2)
    scores = {doc_id: score for doc_id, score in fused}
    score_1 = 1.0 / 61 + 1.0 / 62
    score_3 = 1.0 / 63 + 1.0 / 61
    assert abs(scores[1] - score_1) < 0.001
    assert abs(scores[3] - score_3) < 0.001

def test_rbac_isolation_across_queries():
    qdrant = QdrantService()
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass
    qdrant.init_collection()
    for i in range(10):
        qdrant.add_point(i * 100 + 1, [0.1 + i * 0.01] * 384,
                        {"acl_groups": ["public"], "text": f"public doc {i}"})
        qdrant.add_point(i * 100 + 2, [0.2 + i * 0.01] * 384,
                        {"acl_groups": ["private"], "text": f"private doc {i}"})
    public_only = qdrant.search([0.1] * 384, ["public"], limit=20)
    for point in public_only:
        assert "public" in point.payload.get("acl_groups", [])
        assert "private" not in point.payload.get("acl_groups", [])
    private_only = qdrant.search([0.2] * 384, ["private"], limit=20)
    for point in private_only:
        assert "private" in point.payload.get("acl_groups", [])
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass

def test_retrieve_by_ids_enforces_acl():
    qdrant = QdrantService()
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass
    qdrant.init_collection()
    qdrant.add_point(501, [0.1] * 384, {"acl_groups": ["public"], "text": "public"})
    qdrant.add_point(502, [0.2] * 384, {"acl_groups": ["private"], "text": "private"})

    public_view = qdrant.retrieve_by_ids([501, 502], ["public"])
    assert {int(p.id) for p in public_view} == {501}

    both_view = qdrant.retrieve_by_ids([501, 502], ["public", "private"])
    assert {int(p.id) for p in both_view} == {501, 502}
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass
