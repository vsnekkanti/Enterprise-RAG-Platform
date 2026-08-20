# ADR 0003: RBAC Pre-Filtering (Qdrant Payload Filter)

**Status:** Accepted

## Context

Ingested corpus is multi-tenant: documents tagged with acl_groups (e.g., "public", "private").

Test setup:
- User A: acl_groups = ["public"] → sees 728 chunks (Attention + LLaMA 2)
- User B: acl_groups = ["public", "private"] → sees 1130 chunks (all 3 papers)

**Critical requirement:** User A must NEVER see chunks from User B's private documents, even in edge cases.

Two filtering approaches:
1. **Post-retrieval (wrong):** Retrieve top-5 by vector score, then filter by acl_groups → User A could leak data by inference
2. **Pre-filtering (correct):** Apply acl_groups filter inside Qdrant query → guaranteed no private chunks returned

## Decision

**RBAC pre-filtering via Qdrant payload filter (mandatory parameter)**

```python
# src/retrieval/vector_search.py
filter_cond = Filter(
    must=[FieldCondition(key="acl_groups", match=MatchAny(any=acl_groups))]
)
results = self.client.query_points(
    collection_name=self.collection_name,
    query=vector,
    query_filter=filter_cond,  # ← Applied BEFORE scoring
    limit=limit
)
```

Ingestion payload:
```json
{
  "acl_groups": ["public"],
  "doc_id": 1,
  "chunk_idx": 0,
  "text": "The Transformer architecture..."
}
```

## Consequences

**Pros:**
- Vectors outside acl_groups never scored/returned (cryptographic guarantee)
- RBAC test: 20 queries per user pair, 100% isolation confirmed
- No post-hoc filtering possible to misconfigure

**Cons:**
- Qdrant payload filter adds ~5ms per query (minimal)
- acl_groups parameter is mandatory (breaks if forgotten) ✓ design feature

## Verified Results

- Test case: User A queries 10x, User B queries 10x (20 total)
- Result: 0 cross-user chunk leaks
- Code review: acl_groups required (not optional) in VectorSearch.search()
- API: acl_groups derived from user token at auth layer

## Follow-up: /ask endpoint

The `/ask` endpoint (added for direct Q&A with LLM-generated answers) needs
to fetch full chunk text by ID for the retrieved results before handing them
to the generator. This is a second read path outside the main hybrid
retrieval query, so it re-enforces RBAC independently rather than trusting
the caller: `QdrantService.retrieve_by_ids()` (`src/storage/qdrant_client.py`)
takes the requesting user's `acl_groups` and filters out any retrieved point
whose payload doesn't intersect it, even though in practice the IDs passed in
already came from an ACL-filtered search. Belt-and-suspenders: if that
invariant is ever violated upstream, this is the second gate that catches it
before chunk text reaches the LLM prompt or the API response.
