#!/usr/bin/env python3
import json
import os
import sys
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.getcwd())

from src.storage.db import get_db
from src.storage.models import User
from src.ingestion.embeddings import EmbeddingService
from src.storage.qdrant_client import QdrantService
from pathlib import Path

def load_golden(path: str = "evals/golden.jsonl"):
    with open(path, "r") as f:
        return [json.loads(line) for line in f if line.strip()]

def compute_metrics(golden: list) -> dict:
    print("\n" + "="*70)
    print("COMPUTING EVALUATION METRICS")
    print("="*70)

    from src.retrieval.retriever import HybridRetriever
    from sqlalchemy.orm import joinedload

    retriever = HybridRetriever()
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

    precision_at_5 = []
    recall_at_5 = []

    for i, item in enumerate(golden, 1):
        question = item["question"]
        expected_chunks = set(item["source_chunk_ids"])

        results = retriever.retrieve(question, acl_groups, limit=5)
        retrieved_chunks = set(int(r["id"]) for r in results)

        true_positives = len(retrieved_chunks & expected_chunks)
        precision = true_positives / max(len(retrieved_chunks), 1)
        recall = true_positives / len(expected_chunks) if expected_chunks else 0

        precision_at_5.append(precision)
        recall_at_5.append(recall)

        if (i - 1) % 5 == 0:
            print(f"  [{i}/{len(golden)}] P@5: {precision:.2f}, R@5: {recall:.2f}")

    avg_precision = sum(precision_at_5) / len(precision_at_5)
    avg_recall = sum(recall_at_5) / len(recall_at_5)

    print("\n" + "="*70)
    print("RESULTS")
    print("="*70)
    print(f"Precision@5:  {avg_precision:.4f} ({int(avg_precision*100)}%)")
    print(f"Recall@5:     {avg_recall:.4f} ({int(avg_recall*100)}%)")

    metrics = {
        "precision_at_5": avg_precision,
        "recall_at_5": avg_recall,
        "timestamp": str(Path("evals/baseline.json").stat().st_mtime) if Path("evals/baseline.json").exists() else "new"
    }

    baseline_path = "evals/baseline.json"
    if Path(baseline_path).exists():
        with open(baseline_path, "r") as f:
            baseline = json.load(f)
        print("\n" + "-"*70)
        print(f"Baseline P@5:  {baseline['precision_at_5']:.4f}")
        print(f"Baseline R@5:  {baseline['recall_at_5']:.4f}")
        print(f"Change P@5:    {(avg_precision - baseline['precision_at_5'])*100:+.1f}%")
        print(f"Change R@5:    {(avg_recall - baseline['recall_at_5'])*100:+.1f}%")

        if avg_precision < baseline['precision_at_5'] * 0.95:
            print(f"\n⚠️  REGRESSION: Precision@5 dropped > 5%")
            return 1
    else:
        print(f"\n✓ Saving baseline metrics")
        Path("evals").mkdir(exist_ok=True)
        with open(baseline_path, "w") as f:
            json.dump(metrics, f, indent=2)

    return 0

if __name__ == "__main__":
    golden = load_golden()
    exit_code = compute_metrics(golden)
    sys.exit(exit_code)
