from unittest.mock import patch, MagicMock
from src.retrieval.reranker import CrossEncoderReranker

def test_rerank_empty_candidates_returns_empty():
    reranker = CrossEncoderReranker()
    assert reranker.rerank("query", [], top_k=5) == []

def test_rerank_orders_by_model_score_and_truncates():
    reranker = CrossEncoderReranker()
    candidates = [
        {"id": 1, "text": "irrelevant text"},
        {"id": 2, "text": "highly relevant text"},
        {"id": 3, "text": "somewhat relevant text"},
    ]

    mock_model = MagicMock()
    mock_model.predict.return_value = [0.1, 0.9, 0.5]

    with patch.object(reranker, "_get_model", return_value=mock_model):
        results = reranker.rerank("query", candidates, top_k=2)

    assert [r["id"] for r in results] == [2, 3]
    assert results[0]["score"] == 0.9

def test_rerank_lazily_loads_model_once():
    reranker = CrossEncoderReranker()
    candidates = [{"id": 1, "text": "text"}]

    with patch("sentence_transformers.CrossEncoder") as mock_ce:
        mock_ce.return_value.predict.return_value = [0.3]
        reranker.rerank("q", candidates, top_k=1)
        reranker.rerank("q", candidates, top_k=1)

    mock_ce.assert_called_once()
