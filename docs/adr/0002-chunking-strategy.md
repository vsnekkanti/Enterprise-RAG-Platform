# ADR 0002: Structure-Aware PDF Chunking

**Status:** Accepted

## Context

PDFs contain diverse content: paragraphs, figures, tables, citations. Naive sentence splitting breaks semantic units.

Ingestion test data (3 arXiv papers):
- Attention Is All You Need (1706.03762): 99 chunks
- LLaMA 2: Open Foundation Models (2307.09288): 629 chunks
- Segment Anything (2304.02643): 402 chunks
- **Total: 1130 chunks**

Chunking strategy matters: too small → lost context; too large → diluted query results.

## Decision

**Sentence-based chunking (overlap=50 chars, max_size=500 chars)**

1. Extract full page text via pdfplumber
2. Split on sentence boundaries (regex `(?<=[.!?])\s+`) to preserve meaning
3. Group sentences until chunk_size approaches 500 characters
4. 50-char overlap between chunks for context continuity

```python
# src/ingestion/pdf_processor.py
sentences = re.split(r'(?<=[.!?])\s+', text)
for sentence in sentences:
    test_chunk = current_chunk + " " + sentence if current_chunk else sentence
    if len(test_chunk) < self.max_chunk_size:
        current_chunk = test_chunk
    else:
        chunks.append(Chunk(current_chunk.strip(), page_num, 0))
        current_chunk = sentence
```

## Consequences

**Pros:**
- Respects semantic boundaries (sentence-level)
- Overlapping chunks enable cross-boundary retrieval
- 500-char limit → fits in 384-dim embeddings efficiently

**Cons:**
- Tables split across chunks lose structure (could use advanced table detection)
- Figures: text extraction only (no visual content)

## Follow-up: pdfplumber word-spacing bug

The original naive `text.split(". ")` chunker was masking a deeper bug:
`pdfplumber`'s `extract_text()` was called with its default `x_tolerance=3`,
which merged adjacent words with no space at all on these papers' tightly
kerned two-column layout (e.g. "Atinferencetime" instead of "At inference
time"). No amount of chunking logic could recover spaces that were never
extracted. Fixed by calling `page.extract_text(x_tolerance=1)` in
`src/ingestion/pdf_processor.py`, which correctly treats the smaller
character gaps as word boundaries.

Separately, all three seeded arXiv IDs were wrong — they pointed to
unrelated papers (a PDE transfer-learning paper, Mistral 7B, and QLoRA
instead of the three intended papers). Corrected in `scripts/seed.py`.

## Verified Results

- 1130 chunks across 3 papers ingested successfully, correct paper content confirmed
- Retrieval test: all 25 golden questions retrievable from chunks
- No corrupted or empty chunks; spacing verified readable in generated answers
