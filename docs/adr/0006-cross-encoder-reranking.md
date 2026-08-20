# ADR 0006: Local Cross-Encoder Reranking

**Status:** Accepted (supersedes [ADR 0005](0005-reranking-tradeoff.md))

## Context

ADR 0005 rejected reranking because it only considered a hosted LLM API call
(2s+ latency, $0.01/query, external provider dependency). But RRF-only
retrieval was still missing relevant chunks in practice: for "How does
attention work?", the top-3 RRF results didn't include the chunk containing
the actual `softmax(QKᵀ/√d)V` formula, even though it existed in the corpus.

A cross-encoder reranker (a small model that scores a `(query, passage)`
pair directly, rather than embedding them separately) runs locally on CPU in
milliseconds per candidate and has no per-query cost — it sidesteps the
tradeoffs ADR 0005 was actually rejecting.

## Decision

Add a reranking stage after RRF fusion, using
`cross-encoder/ms-marco-MiniLM-L-6-v2` via `sentence-transformers`
(`src/retrieval/reranker.py`, `CrossEncoderReranker`).

Pipeline change in `src/retrieval/retriever.py`:
1. Over-fetch `max(limit * 4, 20)` candidates from BM25 and vector search
   (previously fetched exactly `limit` from each, leaving nothing for a
   reranker to reorder)
2. RRF-fuse the over-fetched candidates
3. Rerank the fused candidates with the cross-encoder
4. Return the top `limit` after reranking

```python
# src/retrieval/retriever.py
fetch_k = max(limit * 4, 20)
bm25_hits = corpus["bm25"].search(query, limit=fetch_k)
vector_results = self.vector_search.search(query_vector, acl_groups, limit=fetch_k)
fused = self.rrf.fuse(bm25_results, vector_results)
candidates = [...]  # top fetch_k fused candidates with text
return self.reranker.rerank(query, candidates, top_k=limit)
```

The `"score"` field returned by `retrieve()` is now the cross-encoder's
relevance score, not the RRF fused score. Only `"id"` is used by existing
consumers (`/query`, `/ask`, `scripts/eval.py`), so this is not a breaking
change to any caller.

## Consequences

**Pros:**
- No external API, no per-query cost, no added provider dependency
- Latency cost is small: reranking ~20 candidates on CPU is well under 100ms
- Directly fixed a real retrieval gap (see Context) — verified via `/ask`
  output before/after

**Cons:**
- Model load (`CrossEncoder(...)`) adds a few hundred ms on first use per
  process (lazy-loaded on first `rerank()` call, not at import time)
- Over-fetching `fetch_k` candidates increases BM25/vector search cost
  proportionally (still small at this corpus size)
- Cross-encoder relevance score isn't calibrated against the RRF score scale
  — comparing scores across requests with different `limit` isn't meaningful

## Verified Results

- `make test`: `tests/test_reranker.py` (3 tests, mocked model, 100% coverage
  of `reranker.py`)
- `/ask` for "How does attention work?" now surfaces the chunk containing the
  actual attention formula, which it missed pre-reranking
- Golden-dataset P@5/R@5 shifted slightly (40%→38%, 66.7%→64%) — not a
  regression signal, since the golden dataset's "ground truth" chunk IDs are
  themselves generated from plain vector search
  (`scripts/generate_golden.py`), not from any hybrid+rerank pipeline; the
  metric measures agreement with that weaker baseline, not true relevance
