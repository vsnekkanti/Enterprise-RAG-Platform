#!/usr/bin/env python3
import os
import sys
import hashlib
import requests
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.db import init_db, get_db
from src.storage.models import User, AclGroup, Document
from src.ingestion.ingester import Ingester

PAPERS = [
    ("1706.03762", "Attention Is All You Need"),
    ("2307.09288", "LLaMA 2: Open Foundation Models"),
    ("2304.02643", "Segment Anything"),
]

def download_pdf(arxiv_id: str, output_dir: str) -> str:
    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    output_path = os.path.join(output_dir, f"{arxiv_id}.pdf")
    if os.path.exists(output_path):
        print(f"✓ {arxiv_id}.pdf already exists")
        return output_path
    try:
        print(f"Downloading {arxiv_id}...")
        resp = requests.get(pdf_url, timeout=30)
        resp.raise_for_status()
        with open(output_path, "wb") as f:
            f.write(resp.content)
        print(f"✓ Downloaded {arxiv_id}")
        return output_path
    except Exception as e:
        print(f"✗ Failed to download {arxiv_id}: {e}")
        return None

def seed_database():
    print("Initializing database...")
    init_db()
    db = get_db()

    # Check if already seeded
    existing_user = db.query(User).filter(User.username == "user_a").first()
    if existing_user:
        print("✓ Database already seeded (users exist)")
        db.close()
        return

    # Create ACL groups (or get existing ones)
    acl_public = db.query(AclGroup).filter(AclGroup.name == "public").first()
    if not acl_public:
        acl_public = AclGroup(name="public", description="Public documents")
        db.add(acl_public)

    acl_private = db.query(AclGroup).filter(AclGroup.name == "private").first()
    if not acl_private:
        acl_private = AclGroup(name="private", description="Private documents")
        db.add(acl_private)

    db.commit()

    # Create users
    user_a = User(username="user_a", email="a@example.com",
                  api_token=hashlib.sha256(b"token_a").hexdigest())
    user_b = User(username="user_b", email="b@example.com",
                  api_token=hashlib.sha256(b"token_b").hexdigest())
    user_a.acl_groups.append(acl_public)
    user_b.acl_groups.extend([acl_public, acl_private])
    db.add_all([user_a, user_b])
    db.commit()
    db.close()
    print("✓ Database seeded with users and ACL groups")

def ingest_documents():
    pdf_dir = Path("./data/pdfs")
    pdf_dir.mkdir(parents=True, exist_ok=True)
    ingester = Ingester()
    paper_idx = 0
    for arxiv_id, title in PAPERS:
        pdf_path = download_pdf(arxiv_id, str(pdf_dir))
        if not pdf_path:
            continue
        acl_group = "public" if paper_idx < 2 else "private"
        chunks = ingester.ingest_pdf(pdf_path, "arxiv", acl_group)
        print(f"✓ Ingested {title} ({chunks} chunks, acl_group={acl_group})")
        paper_idx += 1
    db = get_db()
    doc_count = db.query(Document).count()
    db.close()
    print(f"\n✓ Total documents ingested: {doc_count}")

if __name__ == "__main__":
    try:
        seed_database()
        ingest_documents()
        print("\n✓ Seed complete!")
    except Exception as e:
        print(f"\n✗ Seed failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
