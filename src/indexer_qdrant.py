import os, json
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

try:
    from .config import EMBEDDING_MODEL, QDRANT_URL, QDRANT_COLLECTION, OUTPUT_JSONL
except ImportError:
    from config import EMBEDDING_MODEL, QDRANT_URL, QDRANT_COLLECTION, OUTPUT_JSONL

def load_rows(path: str) -> List[Dict]:
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            rows.append(json.loads(line))
    return rows

def main():
    if not os.path.exists(OUTPUT_JSONL):
        raise SystemExit(f"Missing corpus: {OUTPUT_JSONL}. Run crawler first.")

    print(f"[indexer] Loading embedding model: {EMBEDDING_MODEL}")
    embedder = SentenceTransformer(EMBEDDING_MODEL)
    dim = embedder.get_sentence_embedding_dimension()
    print(f"[indexer] Embedding dim: {dim}")

    print(f"[indexer] Connecting Qdrant at {QDRANT_URL}")
    client = QdrantClient(QDRANT_URL)

    client.recreate_collection(
        collection_name=QDRANT_COLLECTION,
        vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
    )

    rows = load_rows(OUTPUT_JSONL)
    print(f"[indexer] Rows: {len(rows)}")

    B = 256
    pid = 0
    for i in range(0, len(rows), B):
        batch = rows[i:i+B]
        vecs = embedder.encode([r["content"] for r in batch], normalize_embeddings=True).tolist()
        points = []
        for r, v in zip(batch, vecs):
            points.append(PointStruct(id=pid, vector=v, payload=r))
            pid += 1
        client.upsert(collection_name=QDRANT_COLLECTION, points=points)
        print(f"[indexer] Upserted {i+len(batch)}/{len(rows)}")
    print("[indexer] Done.")

if __name__ == "__main__":
    main()
