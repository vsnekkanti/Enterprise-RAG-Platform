# Enterprise RAG Platform - API Examples

## Setup

Get user tokens:
```bash
TOKEN_A="e7e0ac4358145a17fe33582f906e237bab13f388fcbc564de60b757fb6371f6a"
TOKEN_B="142f2a2e5e1d3066fe8bb2cb63160992fb15b71e64309e59ce555a2f5a720db5"
```

## Example 1: User A Query (public documents only)

User A has access to "public" documents (Attention Is All You Need, LLaMA 2).
`limit` defaults to 8 if omitted. Results are ranked by BM25 + vector + RRF
fusion, then reranked by a cross-encoder (`score` is the cross-encoder's
relevance score, not the RRF fused score — see
[ADR 0006](adr/0006-cross-encoder-reranking.md)).

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"query": "Transformer architecture", "limit": 5}'
```

**Response:**
```json
{
  "query": "Transformer architecture",
  "results": [
    {"id": 154, "score": 0.0164},
    {"id": 110009, "score": 0.0164}
  ],
  "cached": false
}
```

## Example 2: Cached Query (User A, same query)

The second identical query hits the semantic cache (≥0.95 cosine similarity).

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"query": "Transformer architecture", "limit": 5}'
```

**Response:**
```json
{
  "query": "Transformer architecture",
  "results": [
    {"id": 154, "score": 0.0164},
    {"id": 110009, "score": 0.0164}
  ],
  "cached": true
}
```

**Note:** `"cached": true` indicates result served from Redis without re-ranking.

## Example 3: User B Query (public + private documents)

User B has access to both "public" and "private" documents (includes Segment Anything paper).
The same query returns different results because of RBAC pre-filtering in Qdrant.

```bash
curl -X POST http://localhost:8000/query \
  -H "Authorization: Bearer $TOKEN_B" \
  -H "Content-Type: application/json" \
  -d '{"query": "Transformer architecture", "limit": 5}'
```

**Response:**
```json
{
  "query": "Transformer architecture",
  "results": [
    {"id": 154, "score": 0.0164},
    {"id": 110009, "score": 0.0164},
    {"id": 197001, "score": 0.0089}
  ],
  "cached": false
}
```

**Note:** Results include additional chunks from "private" collection that User A cannot see.

## Example 4: Direct Question Answering (/ask endpoint)

Instead of getting chunk IDs, get an LLM-generated answer with sources cited.
Generation runs locally via Ollama (`llama3.1:8b`) using only the retrieved
chunks as context — the model is instructed to answer solely from the
provided context and to say so if the context doesn't contain the answer.

```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Transformer architecture?", "limit": 3}'
```

**Response:**
```json
{
  "query": "What is the Transformer architecture?",
  "answer": "The Transformer architecture is a model that consists of stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, as shown in Figure 1 [1].",
  "sources": [
    {"chunk_id": 320018, "source": "arxiv"}
  ],
  "cached": false
}
```

**Cached answer** (second identical query):
```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Transformer architecture?", "limit": 3}'
```

**Response:**
```json
{
  "query": "What is the Transformer architecture?",
  "answer": "The Transformer architecture is a model that consists of stacked self-attention and point-wise, fully connected layers for both the encoder and decoder, as shown in Figure 1 [1].",
  "sources": [
    {"chunk_id": 320018, "source": "arxiv"}
  ],
  "cached": true
}
```

**Note:** `"cached": true` means the answer was retrieved from Redis cache without re-searching or re-generating. The cache key does not include `limit` or `max_tokens` — re-querying the same question with a different value of either still returns the first call's cached answer until the cache expires or is flushed (`redis-cli FLUSHALL`). See [ADR 0004](adr/0004-semantic-cache-invalidation.md).

## Example 5: Customizing the answer length (max_tokens)

By default, generation is uncapped (`num_predict=-1`: the model generates
until a natural stop or its context limit, not a fixed short cutoff). Pass
`max_tokens` in the request to override this per-call — e.g. to force a
short answer:

```bash
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN_A" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the Transformer architecture?", "limit": 8, "max_tokens": 64}'
```

The server-wide default can also be changed via the `OLLAMA_NUM_PREDICT` env
var before starting the API, without needing a per-request override:

```bash
OLLAMA_NUM_PREDICT=512 python -m src.api.main
```

Other generation settings are also environment-configurable:
- `OLLAMA_URL` (default `http://localhost:11434`) — point at a remote Ollama instance
- `OLLAMA_MODEL` (default `llama3.1:8b`) — swap the local model

**Prerequisite:** Ollama must be running locally with the model pulled:
```bash
ollama pull llama3.1:8b
```

## Example 6: Uploading a document via the API (file upload)

`/ingest` (existing) takes a `file_path` already on the server's disk — not
useful from a browser. `/ingest/upload` accepts a real multipart file
upload instead: it validates the file is a PDF (≤25MB), saves it under
`data/pdfs/` with a sanitized, collision-safe filename, then runs the same
ingestion pipeline as `scripts/seed.py`.

```bash
curl -X POST http://localhost:8000/ingest/upload \
  -H "Authorization: Bearer $TOKEN_A" \
  -F "file=@/path/to/paper.pdf" \
  -F "acl_group=public"
```

**Response:**
```json
{
  "status": "success",
  "filename": "paper.pdf",
  "acl_group": "public",
  "chunks_ingested": 99
}
```

Uploading a non-PDF returns `400`; a file over 25MB returns `413`; ingestion
failures (e.g. malformed PDF) return `500` with a descriptive `detail`. On
success, the uploading user's semantic cache is invalidated so subsequent
`/query`/`/ask` calls see the new content immediately.

## Web UI

A lightweight browser UI is served directly by the API at
`http://localhost:8000/` — a chat interface for `/ask` (with an "Advanced"
panel exposing `limit` and `max_tokens`) and a drag-and-drop upload panel for
`/ingest/upload`. It's a static page (no build step, no separate server) —
just start the API and open the URL. User/token selection is a dropdown of
the two seeded demo users, or a custom-token field for anything else.

## Endpoints Summary

| Endpoint | Purpose | Returns |
|----------|---------|---------|
| `POST /query` | Retrieve chunk IDs | Chunk IDs with scores |
| `POST /ask` | Get actual answer | Full answer text with sources |
| `POST /ingest` | Add new documents (server-side file path) | Status |
| `POST /ingest/upload` | Add new documents (browser file upload) | Status, filename, chunk count |
| `GET /admin/audit` | Audit log | User access history |
| `GET /health` | Health check | Service status |
| `GET /` | Web UI (chat + upload) | HTML page |

## RBAC Security

- Pre-filtering at Qdrant query level: acl_groups filter applied inside vector search
- Per-user cache keyed by user_id; ingest invalidates only that user's cache
- Token auth required on all endpoints
- **Known gap:** any authenticated user can `/ingest` or `/ingest/upload` into
  *any* `acl_group` string, including ones they can't themselves read back
  (e.g. User A, who only belongs to `public`, can currently upload a
  document tagged `acl_group=private`). Pre-existing on `/ingest`; carried
  over unchanged to `/ingest/upload`. Not exploitable to read other users'
  data (RBAC read-side filtering is unaffected), but worth tightening if
  this platform handles real multi-tenant content.
- Both `/query` and `/ask` enforce RBAC
