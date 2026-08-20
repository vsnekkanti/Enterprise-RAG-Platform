from .pdf_processor import PdfProcessor
from .embeddings import EmbeddingService
from src.storage.db import get_db
from src.storage.models import Document
from src.storage.minio_client import MinioService
from src.storage.qdrant_client import QdrantService

class Ingester:
    def __init__(self):
        self.pdf_processor = PdfProcessor()
        self.embeddings = EmbeddingService()
        self.minio = MinioService()
        self.qdrant = QdrantService()

    def ingest_pdf(self, pdf_path: str, source: str, acl_group: str) -> int:
        self.qdrant.init_collection()
        chunks = self.pdf_processor.process(pdf_path)
        minio_path = self.minio.upload(f"{source}/{pdf_path.split('/')[-1]}", pdf_path)
        db = get_db()
        doc = Document(source=source, filename=pdf_path.split('/')[-1],
                       acl_group=acl_group, minio_path=minio_path,
                       chunk_count=len(chunks))
        db.add(doc)
        db.commit()
        doc_id = doc.id
        db.close()
        point_id = doc_id * 10000
        for chunk in chunks:
            vector = self.embeddings.embed_single(chunk.text)
            payload = {
                "doc_id": doc_id,
                "chunk_idx": chunk.chunk_idx,
                "page": chunk.page,
                "text": chunk.text,
                "acl_groups": [acl_group],
                "source": source
            }
            self.qdrant.add_point(point_id, vector, payload)
            point_id += 1
        return len(chunks)
