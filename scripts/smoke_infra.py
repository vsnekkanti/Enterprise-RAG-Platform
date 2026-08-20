#!/usr/bin/env python3
import sys
import time
import psycopg
import requests
from redis import Redis
from qdrant_client import QdrantClient
from minio import Minio

def check_postgres():
    try:
        conn = psycopg.connect(
            host="localhost",
            port=5432,
            user="raguser",
            password="ragpass",
            dbname="rag_db"
        )
        conn.close()
        print("✓ PostgreSQL: healthy")
        return True
    except Exception as e:
        print(f"✗ PostgreSQL: {e}")
        return False

def check_qdrant():
    try:
        client = QdrantClient(
            url="http://localhost:6333",
            api_key="qdrant_key",
            prefer_grpc=False
        )
        client.get_collections()
        print("✓ Qdrant: healthy")
        return True
    except Exception as e:
        print(f"✗ Qdrant: {e}")
        return False

def check_minio():
    try:
        client = Minio(
            "localhost:9000",
            access_key="minioadmin",
            secret_key="minioadmin",
            secure=False
        )
        client.list_buckets()
        print("✓ MinIO: healthy")
        return True
    except Exception as e:
        print(f"✗ MinIO: {e}")
        return False

def check_redis():
    try:
        client = Redis(host="localhost", port=6379, decode_responses=True)
        client.ping()
        print("✓ Redis: healthy")
        return True
    except Exception as e:
        print(f"✗ Redis: {e}")
        return False

def check_jaeger():
    try:
        resp = requests.get("http://localhost:16686/api/traces?service=rag", timeout=5)
        if resp.status_code == 200:
            print("✓ Jaeger: healthy")
            return True
        else:
            print(f"✗ Jaeger: HTTP {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Jaeger: {e}")
        return False

if __name__ == "__main__":
    print("Checking infrastructure health...")
    time.sleep(2)

    results = {
        "PostgreSQL": check_postgres(),
        "Qdrant": check_qdrant(),
        "MinIO": check_minio(),
        "Redis": check_redis(),
        "Jaeger": check_jaeger(),
    }

    print("\n" + "="*40)
    if all(results.values()):
        print("✓ All services healthy!")
        sys.exit(0)
    else:
        failed = [k for k, v in results.items() if not v]
        print(f"✗ Failed services: {', '.join(failed)}")
        sys.exit(1)
