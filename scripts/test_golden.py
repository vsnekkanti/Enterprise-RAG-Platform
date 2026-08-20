#!/usr/bin/env python3
import json
import sys
import os
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())
from src.storage.db import get_db
from src.storage.models import User
from src.ingestion.embeddings import EmbeddingService
from src.storage.qdrant_client import QdrantService

def test_golden_dataset(limit: int = None):
    print("="*70)
    print("TESTING GOLDEN DATASET")
    print("="*70)

    from sqlalchemy.orm import joinedload

    embeddings = EmbeddingService()
    qdrant = QdrantService()

    db = get_db()
    user_a = db.query(User).options(joinedload(User.acl_groups)).filter(User.username == "user_a").first()

    if not user_a:
        db.close()
        print("\n✗ ERROR: user_a not found in database")
        print("   Please run: make seed")
        print("   This will ingest the golden dataset and create demo users")
        sys.exit(1)

    acl_groups = [g.name for g in user_a.acl_groups]
    db.close()

    with open("evals/golden.jsonl", "r") as f:
        questions = [json.loads(line) for line in f if line.strip()]

    if limit:
        questions = questions[:limit]

    results = []
    for i, item in enumerate(questions, 1):
        question = item["question"]
        expected_answer = item["expected_answer"]
        expected_chunks = item["source_chunk_ids"]

        print(f"\n[{i}/{len(questions)}] Q: {question}")
        print(f"    Expected answer: {expected_answer[:60]}...")
        print(f"    Expected chunks: {expected_chunks}")

        query_vec = embeddings.embed_single(question)
        results_from_qdrant = qdrant.search(query_vec, acl_groups, limit=5)

        retrieved_ids = [int(p.id) for p in results_from_qdrant]
        print(f"    Retrieved chunks: {retrieved_ids}")

        matched = sum(1 for c in expected_chunks if c in retrieved_ids)
        print(f"    ✓ Match rate: {matched}/{len(expected_chunks)}")

        results.append({
            "question": question,
            "expected_chunks": expected_chunks,
            "retrieved_chunks": retrieved_ids,
            "matches": matched
        })

    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    total_matches = sum(r["matches"] for r in results)
    total_expected = sum(len(r["expected_chunks"]) for r in results)
    print(f"Total chunk matches: {total_matches}/{total_expected} ({100*total_matches//total_expected}%)")

    perfect = sum(1 for r in results if r["matches"] == len(r["expected_chunks"]))
    print(f"Questions with 100% match: {perfect}/{len(results)}")

    partial = sum(1 for r in results if 0 < r["matches"] < len(r["expected_chunks"]))
    print(f"Questions with partial match: {partial}/{len(results)}")

    miss = sum(1 for r in results if r["matches"] == 0)
    print(f"Questions with no match: {miss}/{len(results)}")

    print("\nQuestions needing review:")
    for r in results:
        if r["matches"] == 0:
            print(f"  ✗ {r['question'][:50]}...")

if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else None
    test_golden_dataset(limit)
