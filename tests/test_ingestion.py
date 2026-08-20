import pytest
from sqlalchemy import text
from src.storage.db import get_db, init_db
from src.storage.models import Document, User, AclGroup
from src.storage.qdrant_client import QdrantService

@pytest.fixture(scope="function", autouse=True)
def setup_db():
    init_db()
    qdrant = QdrantService()
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass
    yield
    db = get_db()
    db.execute(text("DELETE FROM user_acl_groups"))
    db.execute(text("DELETE FROM documents"))
    db.execute(text("DELETE FROM users"))
    db.execute(text("DELETE FROM acl_groups"))
    db.commit()
    db.close()
    try:
        qdrant.client.delete_collection(qdrant.collection_name)
    except Exception:
        pass

def test_postgres_ingestion_records():
    import time
    unique_name = f"test_group_{int(time.time() * 1000)}"
    db = get_db()
    acl_group = AclGroup(name=unique_name, description="Test")
    db.add(acl_group)
    db.commit()
    doc = Document(source="test", filename="test.pdf", acl_group=unique_name,
                   minio_path="s3://bucket/test.pdf", chunk_count=10)
    db.add(doc)
    db.commit()
    doc_id = doc.id
    db.close()
    db = get_db()
    retrieved = db.query(Document).filter(Document.id == doc_id).first()
    assert retrieved is not None
    assert retrieved.chunk_count == 10
    assert retrieved.acl_group == unique_name
    db.close()

def test_qdrant_acl_groups_payload():
    qdrant = QdrantService()
    qdrant.init_collection()
    payload = {
        "doc_id": 1,
        "chunk_idx": 0,
        "acl_groups": ["public"],
        "text": "Test chunk"
    }
    qdrant.add_point(1, [0.1] * 384, payload)
    results = qdrant.search([0.1] * 384, ["public"], limit=1)
    assert len(results) > 0
    assert results[0].payload["acl_groups"] == ["public"]

def test_rbac_isolation():
    qdrant = QdrantService()
    qdrant.init_collection()
    qdrant.add_point(1, [0.1] * 384, {"acl_groups": ["public"], "text": "Public"})
    qdrant.add_point(2, [0.2] * 384, {"acl_groups": ["private"], "text": "Private"})
    public_results = qdrant.search([0.1] * 384, ["public"], limit=10)
    assert len(public_results) == 1
    assert public_results[0].payload["text"] == "Public"
    private_results = qdrant.search([0.1] * 384, ["private"], limit=10)
    assert len(private_results) == 1
    assert private_results[0].payload["text"] == "Private"
