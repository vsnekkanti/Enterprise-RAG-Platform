#!/usr/bin/env python3
"""
Quick test script for the /ask endpoint.
Make sure to:
1. Run: make up
2. Run: make seed
3. Run: python -m src.api.main (in another terminal)
4. Then run this script
"""
import requests
import json

BASE_URL = "http://localhost:8000"

# Tokens from seeded users
USER_A_TOKEN = "e7e0ac4358145a17fe33582f906e237bab13f388fcbc564de60b757fb6371f6a"
USER_B_TOKEN = "142f2a2e5e1d3066fe8bb2cb63160992fb15b71e64309e59ce555a2f5a720db5"

def test_ask_endpoint():
    print("="*70)
    print("TESTING /ask ENDPOINT (Direct Question Answering)")
    print("="*70)

    questions = [
        "What is the Transformer architecture?",
        "How does attention work?",
        "What is LLaMA?",
    ]

    for i, question in enumerate(questions, 1):
        print(f"\n[{i}/{len(questions)}] Question: {question}")
        print("-" * 70)

        response = requests.post(
            f"{BASE_URL}/ask",
            headers={"Authorization": f"Bearer {USER_A_TOKEN}"},
            json={"query": question, "limit": 8}
        )

        if response.status_code == 200:
            data = response.json()
            print(f"Cached: {data['cached']}")
            print(f"\nAnswer:\n{data['answer']}")
            print(f"\nSources: {data['sources']}")
        else:
            print(f"✗ Error: {response.status_code}")
            print(response.text)

if __name__ == "__main__":
    try:
        test_ask_endpoint()
        print("\n" + "="*70)
        print("✓ /ask endpoint working!")
        print("="*70)
    except Exception as e:
        print(f"\n✗ Error: {e}")
        print("\nMake sure:")
        print("1. Services are running: make up")
        print("2. Database is seeded: make seed")
        print("3. API is running: python -m src.api.main")
