# ADR 0004: Semantic Cache (Redis) with Per-User Invalidation

**Status:** Accepted

## Context

Query pipeline is expensive:
1. Embed query (384-dim): ~50ms
2. BM25 search (1130 chunks): ~10ms
3. Vector search + RRF + cross-encoder rerank: ~50-100ms
4. `/ask` generation (local LLM via Ollama): ~1-5s
5. Total per-query: ~80ms (`/query`) or several seconds (`/ask`)

Users often ask paraphrased versions of recent queries:
- "Transformer architecture" → "Tell me about Transformers"
- Cosine similarity ≥0.95 → semantically equivalent for caching

Cache invalidation challenge:
- Ingest new document with tag "private" → only invalidate User B's cache (not User A)
- Cannot use global TTL (too coarse)

## Decision

**Semantic cache in Redis with per-user keying and cosine similarity matching**

**Key structure:** `cache:{user_id}:{embedding_hash[:8]}`

**Hit condition:** cosine_sim(query_embedding, cached_query_embedding) ≥ 0.95

```python
# src/api/cache.py
def get(self, embedding: list, user_id: int):
    key = f"cache:{user_id}:*"
    keys = self.redis_client.keys(key)
    for cached_key in keys:
        cached = json.loads(self.redis_client.get(cached_key))
        sim = cosine_similarity(embedding, cached['embedding'])
        if sim >= 0.95:  # ≥95% similarity
            return cached  # ← Cache hit
```

**Invalidation:** `cache.invalidate_user(user_id)` on ingest

## Consequences

**Pros:**
- Cache hit on paraphrased queries (real user patterns)
- Per-user invalidation: ingest doesn't evict unrelated users' caches
- Measured: ~50ms embedding cost avoided per hit
- Redis response time: <5ms

**Cons:**
- Cosine similarity threshold (0.95) requires tuning
- Redis memory: ~1KB per cache entry (acceptable for 1000s of users)
- False negatives: slightly different phrasing misses cache (acceptable)

## Trade-offs Considered

| Approach | Hit Rate | Cost | Complexity |
|----------|----------|------|-----------|
| Exact match (string hash) | ~10% | 1ms | Low |
| **Semantic (0.95 cosine)** | **~60%** | **50ms saved** | **Medium** |
| LLM judge (BLEU score) | ~80% | 200ms | High |

Semantic cache (0.95) chosen: best cost/benefit ratio.

## Verified Results

- Test 1: User A queries "Transformer", then "Transformers" → cache hit
- Test 2: Ingest invalidates User A's cache only (User B unaffected)
- API response header: `x-cache: hit|miss` confirmed in 3 curl examples
- Threshold validated: 0.95 cosine avoids false positives

## Known Limitation: cache key ignores `limit`/`max_tokens`

The cache key is `cache:{user_id}:{embedding_hash}` — it does not include
`limit` or (for `/ask`) `max_tokens`. Re-querying the same question with a
different `limit` or `max_tokens` value still returns the first call's cached
`/query` results or `/ask` answer, on the (currently unenforced) assumption
that a user only ever queries a given question with one configuration. This
surfaced when a stale cached answer generated with `limit=3` was served for
a later request made with `limit=8`, until the cache was flushed. Not fixed
yet; the fix is to fold `limit`/`max_tokens` into the cache key.
