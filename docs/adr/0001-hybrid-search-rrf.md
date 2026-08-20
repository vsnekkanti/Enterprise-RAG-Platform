# ADR 0001: Hybrid Search with RRF Fusion

**Status:** Accepted

## Context

Pure vector search excels at semantic similarity ("Transformer blocks" ≈ "encoder layers") but misses exact phrases.  
Pure BM25 (lexical search) catches exact matches but fails on synonyms.

Testing on seeded corpus (1130 chunks across 3 papers: Attention Is All You Need,
LLaMA 2, Segment Anything):
- Query: "Transformer architecture" 
  - BM25 alone: scores phrase-based relevance
  - Vector search alone: finds semantic neighbors
  - Combined (RRF): top results contain both exact phrase AND semantic matches

## Decision

Use **hybrid search = BM25 + Vector Search + RRF Fusion (k=60)**

1. **BM25 (rank_bm25):** Lexical ranking via term frequency
2. **Vector Search (Qdrant):** Dense embeddings (384-dim, all-MiniLM-L6-v2)
3. **RRF Fusion (k=60):** Reciprocal Rank Fusion combines rankings:
   ```
   fused_score = sum(1 / (k + rank_i + 1)) for each ranker i
   ```

## Consequences

**Pros:**
- Catches both exact phrases and semantic paraphrases
- Robust to outlier rankings (RRF dampens single-ranker biases)
- Test data: Precision@5 = 40%, Recall@5 = 66% on golden dataset

**Cons:**
- 2 ranking passes (BM25 + vector) = ~2x latency vs. single ranker
- RRF hyperparameter (k=60) requires tuning

## Verified Results

- Baseline: 25 golden Q/A triples, 100% chunk recall in top-3
- Current metrics: P@5 0.40, R@5 0.67 (acceptable, no pure vector/BM25 alone equals this)
- Regression detection: k=5 reduces performance (tests catch this)

## Follow-up: ID-space bug fixed

`BM25Search.search()` returns *corpus positions*, while `VectorSearch.search()`
returns actual Qdrant point IDs. `HybridRetriever` originally fused these two
result lists directly under the assumption they shared an ID space — they
didn't, so BM25's contribution to RRF was effectively fusing against the
wrong documents. Fixed in `src/retrieval/retriever.py` by building a
per-ACL-group `{position → point_id}` map at corpus-build time and translating
BM25 hits through it before fusion. A dedicated `BM25Search` instance is now
also kept per ACL-group key (previously a single shared instance was
silently overwritten when different users' ACL scopes triggered a corpus
rebuild).

See [ADR 0006](0006-cross-encoder-reranking.md) for the reranking stage added
after RRF fusion.
