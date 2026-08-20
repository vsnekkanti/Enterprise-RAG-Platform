import os
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from .auth import get_current_user, get_user_acl_groups
from .cache import SemanticCache
from .uploads import save_upload
from src.storage.models import User
from src.ingestion.embeddings import EmbeddingService
from src.services.generation import AnswerGenerator, GenerationError

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Enterprise RAG Platform")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
cache = SemanticCache()
embeddings = EmbeddingService()
generator = AnswerGenerator()
retriever = None

def get_retriever():
    global retriever
    if retriever is None:
        from src.retrieval.retriever import HybridRetriever
        retriever = HybridRetriever()
    return retriever

class QueryRequest(BaseModel):
    query: str
    limit: int = 8
    max_tokens: Optional[int] = None

class QueryResponse(BaseModel):
    query: str
    results: list
    cached: bool

class AnswerResponse(BaseModel):
    query: str
    answer: str
    sources: list
    cached: bool

@app.get("/")
async def ui() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.post("/query")
async def query(
    req: QueryRequest,
    user: dict = Depends(get_current_user),
    acl_groups: list = Depends(get_user_acl_groups)
) -> QueryResponse:
    try:
        query_embedding = embeddings.embed_single(req.query)
        cached_result = cache.get(query_embedding, user["id"])
        if cached_result:
            return QueryResponse(
                query=req.query,
                results=cached_result.get("results", []),
                cached=True
            )
        ret = get_retriever()
        results = ret.retrieve(req.query, acl_groups, limit=req.limit)
        response = QueryResponse(query=req.query, results=results, cached=False)
        cache.set(query_embedding, response.dict(), user["id"])
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest")
async def ingest(
    source: str,
    file_path: str,
    acl_group: str,
    user: dict = Depends(get_current_user)
) -> dict:
    from src.ingestion.ingester import Ingester
    ingester = Ingester()
    chunks = ingester.ingest_pdf(file_path, source, acl_group)
    cache.invalidate_user(user["id"])
    return {"status": "success", "chunks_ingested": chunks}

@app.post("/ingest/upload")
async def ingest_upload(
    file: UploadFile = File(...),
    acl_group: str = Form(...),
    user: dict = Depends(get_current_user)
) -> dict:
    disk_path, original_name = await save_upload(file)
    try:
        from src.ingestion.ingester import Ingester
        ingester = Ingester()
        chunks = ingester.ingest_pdf(disk_path, "upload", acl_group)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {e}")
    cache.invalidate_user(user["id"])
    return {
        "status": "success",
        "filename": original_name,
        "acl_group": acl_group,
        "chunks_ingested": chunks
    }

@app.get("/admin/audit")
async def audit(user: dict = Depends(get_current_user)) -> dict:
    return {
        "user_id": user["id"],
        "username": user["username"],
        "acl_groups": user["acl_groups"],
        "message": "Audit endpoint placeholder"
    }

@app.post("/ask")
async def ask(
    req: QueryRequest,
    user: dict = Depends(get_current_user),
    acl_groups: list = Depends(get_user_acl_groups)
) -> AnswerResponse:
    try:
        query_embedding = embeddings.embed_single(req.query)
        cached_result = cache.get(query_embedding, user["id"])
        cached = cached_result is not None

        if cached_result:
            return AnswerResponse(
                query=req.query,
                answer=cached_result.get("answer", ""),
                sources=cached_result.get("sources", []),
                cached=True
            )

        ret = get_retriever()
        results = ret.retrieve(req.query, acl_groups, limit=req.limit)

        from src.storage.qdrant_client import QdrantService
        qdrant = QdrantService()

        point_ids = [result["id"] for result in results]
        points_by_id = {
            int(p.id): p for p in qdrant.retrieve_by_ids(point_ids, acl_groups)
        }

        source_chunks = [
            {
                "chunk_id": result["id"],
                "text": points_by_id[result["id"]].payload.get("text", ""),
                "doc_id": points_by_id[result["id"]].payload.get("doc_id", ""),
                "source": points_by_id[result["id"]].payload.get("source", "")
            }
            for result in results if result["id"] in points_by_id
        ]

        try:
            answer = generator.generate(req.query, source_chunks, num_predict=req.max_tokens)
        except GenerationError as e:
            raise HTTPException(status_code=503, detail=str(e))

        response = AnswerResponse(
            query=req.query,
            answer=answer,
            sources=[
                {"chunk_id": c["chunk_id"], "source": c["source"]}
                for c in source_chunks
            ],
            cached=False
        )

        cache.set(query_embedding, {
            "answer": answer,
            "sources": response.sources
        }, user["id"])

        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
