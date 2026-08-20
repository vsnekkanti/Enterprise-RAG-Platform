import pdfplumber
from typing import List, Tuple

class Chunk:
    def __init__(self, text: str, page: int, chunk_idx: int):
        self.text = text
        self.page = page
        self.chunk_idx = chunk_idx

class PdfProcessor:
    def __init__(self, max_chunk_size: int = 500, overlap: int = 50):
        self.max_chunk_size = max_chunk_size
        self.overlap = overlap

    def process(self, pdf_path: str) -> List[Chunk]:
        chunks = []
        chunk_id = 0
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text(x_tolerance=1)
                if not text:
                    continue
                page_chunks = self._chunk_page(text, page_num)
                for chunk in page_chunks:
                    chunk.chunk_idx = chunk_id
                    chunks.append(chunk)
                    chunk_id += 1
        return chunks

    def _chunk_page(self, text: str, page_num: int) -> List[Chunk]:
        import re
        # Clean up text: normalize whitespace but preserve paragraph breaks
        text = re.sub(r'\s+', ' ', text).strip()

        # Split on sentence boundaries (., !, ?)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            # Add sentence (it doesn't have trailing space yet)
            sentence = sentence.strip()
            if not sentence:
                continue

            # Check if adding this sentence would exceed max size
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence

            if len(test_chunk) < self.max_chunk_size:
                current_chunk = test_chunk
            else:
                if current_chunk:
                    chunks.append(Chunk(current_chunk.strip(), page_num, 0))
                current_chunk = sentence

        if current_chunk:
            chunks.append(Chunk(current_chunk.strip(), page_num, 0))
        return chunks
