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

embeddings = EmbeddingService()
qdrant = QdrantService()
db = get_db()
user_a = db.query(User).filter(User.username == "user_a").first()
acl_groups = [g.name for g in user_a.acl_groups]
db.close()

questions = [
    ("What is the Transformer architecture based on?", "The Transformer architecture is based on attention mechanisms, specifically self-attention."),
    ("What are the main components of the Transformer?", "The Transformer consists of an encoder-decoder structure with multi-head attention layers and feed-forward networks."),
    ("What is self-attention in Transformers?", "Self-attention allows each position in the sequence to attend to all other positions."),
    ("How does multi-head attention work?", "Multi-head attention runs multiple attention operations in parallel."),
    ("What is the role of positional encoding?", "Positional encoding adds information about the position of tokens in the sequence."),
    ("What is LLaMA?", "LLaMA is a collection of foundation language models ranging from 7B to 65B parameters."),
    ("What are the key features of LLaMA 2?", "LLaMA 2 improvements include better performance and longer context windows."),
    ("How was LLaMA trained?", "LLaMA was trained using an autoregressive transformer-based approach on large text corpora."),
    ("What is Segment Anything (SAM)?", "Segment Anything is a foundation model for image segmentation that can segment any object."),
    ("How does Segment Anything work?", "SAM uses a vision transformer encoder and a mask decoder for segmentation."),
    ("What are the prompt types supported by SAM?", "SAM supports interactive points, bounding boxes, and text descriptions."),
    ("What is the advantage of Transformers over RNNs?", "Transformers allow parallel processing and better long-range dependencies."),
    ("How is attention computed in Transformers?", "Attention is computed using scaled dot-product attention."),
    ("What is the feed-forward network in Transformers?", "The feed-forward network consists of linear transformations with ReLU activation."),
    ("How does layer normalization work?", "Layer normalization normalizes across features to stabilize training."),
    ("What is the purpose of dropout?", "Dropout prevents overfitting by randomly deactivating neurons during training."),
    ("How does LLaMA compare to GPT-3?", "LLaMA 7B can outperform GPT-3 in many benchmarks."),
    ("What are ethical considerations for LLMs?", "Key considerations include bias, potential misuse, and environmental impact."),
    ("How is SAM different from traditional methods?", "SAM generalizes to new tasks without task-specific training."),
    ("What is zero-shot segmentation?", "Zero-shot segmentation refers to segmenting without prior training on specific classes."),
    ("How was SAM evaluated?", "SAM was evaluated on diverse segmentation benchmarks."),
    ("What is the computational complexity of Transformers?", "Transformers have O(n^2) complexity due to all-pairs attention."),
    ("How are Transformers pre-trained?", "Using masked language modeling or causal language modeling on large corpora."),
    ("What is fine-tuning in Transformers?", "Adapting a pre-trained model to downstream tasks with small learning rates."),
    ("What makes Transformers effective for NLP?", "Their ability to parallelize and capture long-range dependencies makes them effective."),
]

golden = []
for question, expected_answer in questions:
    query_vec = embeddings.embed_single(question)
    results = qdrant.search(query_vec, acl_groups, limit=3)
    chunk_ids = [int(p.id) for p in results]
    golden.append({
        "question": question,
        "expected_answer": expected_answer,
        "source_chunk_ids": chunk_ids
    })
    print(f"✓ {question[:50]}... → chunks {chunk_ids}")

with open("evals/golden.jsonl", "w") as f:
    for item in golden:
        f.write(json.dumps(item) + "\n")

print(f"\n✓ Generated {len(golden)} golden examples")
