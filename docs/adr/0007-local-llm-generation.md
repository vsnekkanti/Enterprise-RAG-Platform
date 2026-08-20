# ADR 0007: Local LLM Answer Generation for /ask

**Status:** Accepted

## Context

The `/ask` endpoint was added to answer questions directly instead of
returning bare chunk IDs (unlike `/query`). Its first implementation only
concatenated the retrieved chunks' raw text with a `[source #id]` prefix —
there was no generation step at all. This meant answers were literally
verbatim excerpts (sometimes a bibliography or references section, if that's
what ranked first), not synthesized responses, defeating the point of a
question-answering endpoint.

Options for the missing generation step:
1. Hosted LLM API (e.g. Anthropic, OpenAI) — best quality, requires an API
   key and per-call cost, external dependency
2. Local model via Ollama — no API key or per-call cost, runs entirely
   on-machine, weaker quality ceiling than a frontier hosted model
3. Extractive-only improvement (better snippet selection, no generation) —
   free, but still not real answer synthesis

## Decision

**Local generation via Ollama, `llama3.1:8b`** (`src/services/generation.py`,
`AnswerGenerator`).

- Prompt instructs the model to answer *only* from the retrieved chunks
  (passed as numbered `[N]` context blocks) and to say so if the context
  doesn't contain the answer, rather than filling gaps from its own
  training data
- `OLLAMA_URL` / `OLLAMA_MODEL` env vars make the host and model swappable
  (e.g. to point at a different local model or a remote Ollama instance)
- `OLLAMA_NUM_PREDICT` env var (default `-1`, meaning "no artificial cap —
  generate until a natural stop or the model's context limit") controls
  maximum output length; overridable per-request via `max_tokens` in the
  `/ask` request body, which flows through to `AnswerGenerator.generate(...,
  num_predict=...)`
- `OLLAMA_TEMPERATURE` env var (default `0.3`, below Ollama's own `0.8`
  default) favors direct, consistent answers over creative variation —
  see Update below for why this matters more than it sounds

```python
# src/services/generation.py
resp = requests.post(
    f"{self.url}/api/generate",
    json={
        "model": self.model,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": effective_num_predict}
    },
    timeout=120
)
```

## Consequences

**Pros:**
- No API key, no per-query cost, no external network dependency at request
  time (only needed once, to `ollama pull llama3.1:8b`)
- Honest failure mode: when retrieval doesn't surface the right chunk, the
  model says the context doesn't contain the answer instead of hallucinating
- Configurable output length closes a real gap: the previous hardcoded call
  had no `options.num_predict`, and Ollama's per-model default cutoff could
  silently truncate longer answers

**Cons:**
- `llama3.1:8b` is meaningfully weaker than a frontier hosted model —
  reasoning over subtle or multi-hop questions will be worse
- Adds a runtime dependency (Ollama must be running with the model pulled)
  not managed by `docker-compose.yml` — a fresh clone needs
  `ollama pull llama3.1:8b` as an extra manual step beyond `make up`
- Generation latency (~1-5s per `/ask` call) is far higher than `/query`'s
  ~80ms — acceptable for direct Q&A, not for high-throughput retrieval

## Verified Results

- `make test`: `tests/test_generation.py` (4 tests, mocked HTTP calls, 100%
  coverage of `generation.py`)
- Manual verification via `scripts/test_ask_api.py`: answers are coherent,
  cited, and correctly decline to answer when context is insufficient (e.g.
  "What is LLaMA?" against a corpus that only discusses "Llama 2" specifics)
- Confirmed no truncation on longer answers after setting `num_predict=-1`
  (previously relied on Ollama's implicit per-model default)

## Follow-up: hedging noise and model upgrade

Testing surfaced a different problem than factual quality: the initial
model (`llama3.2:3b`) would find the right information across multiple
chunks but wrap it in defensive meta-commentary — e.g. "Unfortunately, the
context provided does not contain explicit guidelines... however it does
provide guidelines as mentioned in [Source 3]... There is no comprehensive
set of simple guidelines provided" — even when the answer was fully
present, just spread across several chunks. The original prompt's only
instruction on this was "If the context doesn't contain the answer, say
so", which a small model over-applied to *partial* answers instead of only
*absent* ones.

Three changes addressed this:
1. **Prompt rewrite** (`_build_prompt` in `src/services/generation.py`):
   explicitly instructs the model to synthesize information across sources
   into one coherent answer, to not comment on what the context does or
   doesn't "explicitly" contain, and to only decline (in one short sentence)
   when *none* of the context is relevant — not when the answer is merely
   scattered across sources. Citation format simplified from
   `[Source N: source #chunk_id]` to `[N]` — the verbose form was noise
   inline; full source metadata is already returned separately in the
   API response's `sources` field and rendered as badges in the UI.
2. **Model upgrade**: default `OLLAMA_MODEL` changed from `llama3.2:3b` to
   `llama3.1:8b`. A ~5GB additional download and roughly 2-3x the per-answer
   latency on CPU (~8-28s per `/ask` call vs ~2-10s before, depending on
   context size), for meaningfully better instruction-following — the 3B
   model was more prone to the hedging pattern above regardless of prompt
   wording; the 8B model follows the "don't hedge on partial answers"
   instruction reliably.
3. **Temperature**: added `OLLAMA_TEMPERATURE` (default `0.3`) — lower than
   Ollama's `0.8` default, favoring consistent, focused synthesis over
   variety, which suits grounded Q&A better than open-ended writing.

Verified against a health-guidelines PDF with the question "what are the
guidelines for exercise in simple terms?": before, the answer led with
several sentences of hedging before finally listing partial bullet points;
after, it opens directly with a synthesized list combining all relevant
chunks, no hedging, and correctly still declines in one sentence for
genuinely out-of-context questions (tested with an unrelated factual
question against the same corpus — no hallucination).

This does not fully close the gap to a frontier hosted model — see Cons
above, still applicable — but it removes the specific noise pattern that
made answers look broken rather than just occasionally imperfect.
