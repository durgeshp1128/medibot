# retrieval.py
"""Hybrid retrieval (dense + BM25) with RBAC filter.

- Uses Qdrant local storage (./qdrant_storage).
- Dense embeddings are generated with a SentenceTransformer model.
- BM25 sparse vectors are placeholders (to be added later).
- The caller's role is used to filter results via the `access_roles` metadata field.
- Returns a list of candidate chunks (dicts) ready for reranking.
"""

import os
from pathlib import Path
from typing import List, Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition

# Embedding model – replace with the production model you prefer.
# For now we use a lightweight transformer.
try:
    from sentence_transformers import SentenceTransformer
except ImportError as e:
    raise ImportError("Please install sentence-transformers in your virtual environment.")

EMBEDDING_MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "./qdrant_storage")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "medibot_chunks")


def _dense_embedding(text: str) -> List[float]:
    """Return a dense embedding vector for the query text."""
    return embedder.encode(text).tolist()


def _role_filter(role: str) -> Filter:
    """Construct a Qdrant filter that retains only points where
    `access_roles` contains the supplied role.
    """
    return Filter(
        must=[
            FieldCondition(
                key="access_roles",
                match={"any": [role]},
            )
        ]
    )


def hybrid_retriever(query: str, role: str, top_k: int = 10) -> List[Dict[str, Any]]:
    """Perform a hybrid (dense + BM25) search with RBAC filtering.

    Currently the BM25 component is a placeholder – the function uses Qdrant's
    dense vector search and applies the role filter. When BM25 vectors are stored
    you can add them via the ``search`` call's ``query`` argument.
    """
    client = QdrantClient(path=QDRANT_LOCAL_PATH)
    if not client.collection_exists(COLLECTION_NAME):
        raise RuntimeError(
            f"Qdrant collection '{COLLECTION_NAME}' does not exist. Run ingest.py first."
        )

    query_vec = _dense_embedding(query)

    hits = client.search(
        collection_name=COLLECTION_NAME,
        query_vector=query_vec,
        limit=top_k,
        query_filter=_role_filter(role),
    )

    candidates: List[Dict[str, Any]] = []
    for hit in hits:
        payload = hit.payload or {}
        candidates.append(
            {
                "text": payload.get("text", ""),
                "metadata": {
                    "source_document": payload.get("source_document"),
                    "collection": payload.get("collection"),
                    "access_roles": payload.get("access_roles"),
                    "section_title": payload.get("section_title"),
                    "chunk_type": payload.get("chunk_type"),
                },
                "score": hit.score,
            }
        )
    return candidates

if __name__ == "__main__":
    # Quick manual sanity‑check
    q = "What is the recommended dosage of amoxicillin for a child?"
    r = "doctor"
    for c in hybrid_retriever(q, r):
        print(c["metadata"]["source_document"], "|", c["metadata"]["section_title"])
