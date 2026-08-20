# ADR 0005: Reranking via LLM vs. RRF (Cost/Latency Tradeoff)

**Status:** Superseded by [ADR 0006](0006-cross-encoder-reranking.md)

> **Note:** This ADR only evaluated reranking via a *hosted LLM API call*
> (e.g. GPT-4) and rejected it on cost/latency grounds. It did not consider
> a local cross-encoder model, which has neither the latency nor the
> per-query cost problem described below. Reranking was later added using
> exactly that approach — see ADR 0006. The analysis below is kept for
> historical context on why LLM-based reranking specifically was rejected.

## Context

Hybrid retrieval (BM25 + Vector + RRF) achieves Precision@5 = 40%, Recall@5 = 66%.

Could improve by reranking top-10 results with LLM (e.g., GPT-4):
- Query: "Transformer architecture"
- Initial ranking: top-10 via RRF
- Rerank: send top-10 + query to LLM → get relevance scores
- Return top-5 after reranking

Trade-offs:

| Metric | RRF Only | RRF + LLM Rerank |
|--------|----------|------------------|
| Precision@5 | 40% | ~50% (estimated) |
| P99 Latency | 150ms | 2000ms (LLM call) |
| Cost per query | <$0.001 | $0.01 (LLM tokens) |
| Operational complexity | Low | High (LLM provider, fallback) |

## Decision

**NOT implementing LLM reranking; retain RRF-only architecture**

Rationale:
1. **Latency budget:** API P99 latency target ~500ms; LLM adds 2s+ latency
2. **Cost:** 40% → 50% precision gain costs 10x more per query
3. **Operational:** LLM provider dependency; fallback logic complexity
4. **Data:** Golden dataset validates RRF achieves ~0.67 recall on target corpus

For future: implement reranking as optional feature (flag) if precision becomes critical bottleneck.

## Implementation Notes

RRF configuration is tunable:
```python
# src/retrieval/rrf.py
rrf = RRF(k=60)  # k is hyperparameter; can be adjusted if needed
```

If precision needs improvement without LLM:
- Increase k to weight earlier ranks more
- Adjust BM25 parameters (already using defaults)
- Gather more training data for fine-tuned embeddings

## Verified Results

- Baseline precision: 40% (25 golden Q/A, top-5 retrieval)
- Regression test: k=5 reduces precision (tests catch this)
- Acceptable for MVP; reranking deferred to optimization phase
- Cost-benefit: current approach balances latency, cost, quality
