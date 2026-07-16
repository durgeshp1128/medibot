import os
from typing import Dict, Any, List
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny, MatchValue, Prefetch

# Dense Embedding Model (Semantic Search)
from sentence_transformers import SentenceTransformer
# Sparse Embedding Model (BM25 Keyword Search)
from fastembed import SparseTextEmbedding
from backend.app.graph.state import AgentState

# Initialize clients (In production, these should be loaded once globally)
import pathlib
# Resolve absolute path to the Qdrant storage directory (project_root/data/qdrant_storage)
_qdrant_storage_path = pathlib.Path(__file__).resolve().parents[3] / "data" / "qdrant_storage"
qdrant_client = QdrantClient(path=str(_qdrant_storage_path))
# Ensure the collection exists (create if missing)
from qdrant_client.http.models import VectorParams, Distance
try:
    # We want named vectors: "dense" and "sparse"
    # To be absolutely sure we update the configuration if it was already created with a single unnamed vector,
    # we can check if "dense" vector is configured. If not, recreate.
    info = qdrant_client.get_collection("medibot_documents")
    if "dense" not in info.config.params.vectors:
        raise ValueError("Recreate collection with named vectors")
except Exception:
    from qdrant_client.http.models import VectorParams, Distance
    # Recreate collection with both "dense" (SentenceTransformer) and "sparse" (BM25) vector settings
    # Note: For sparse vectors, Qdrant in python-client uses SparseVectorParams. Let's configure it.
    from qdrant_client.http.models import SparseVectorParams, SparseVectorConfig
    qdrant_client.recreate_collection(
        collection_name="medibot_documents",
        vectors_config={
            "dense": VectorParams(size=384, distance=Distance.COSINE)
        },
        sparse_vectors_config={
            "sparse": SparseVectorParams()
        }
    )

dense_model = SentenceTransformer("all-MiniLM-L6-v2")
sparse_model = SparseTextEmbedding(model_name="Qdrant/bm25")

def retrieve_node(state: AgentState) -> AgentState:
    """
    LangGraph Node: Executes a Hybrid Search (Dense + Sparse) against Qdrant.
    Enforces Role-Based Access Control (RBAC) purely at the database level.
    """
    question = state["question"]
    user_role = state["user_role"]
    allowed_collections = state["allowed_collections"]

    print(f"🔍 Executing Hybrid Retrieval for role: [{user_role}]")

    # ---------------------------------------------------------
    # 1. HARD RBAC FILTER (The Security Gate)
    # ---------------------------------------------------------
    # This filter guarantees that even if the LLM is jailbroken, 
    # Qdrant will physically refuse to return restricted documents.
    rbac_filter = Filter(
        must=[
            # Condition 1: Chunk must belong to one of the user's allowed collections
            FieldCondition(
                key="collection",
                match=MatchAny(any=allowed_collections)
            ),
            # Condition 2: The specific user role must be present in the chunk's access_roles array
            FieldCondition(
                key="access_roles",
                match=MatchValue(value=user_role)
            )
        ]
    )

    # ---------------------------------------------------------
    # 2. GENERATE VECTORS (Dense + Sparse)
    # ---------------------------------------------------------
    # Dense Vector (Understands "cardiovascular issues" = "heart problems")
    dense_vector = dense_model.encode(question).tolist()
    #print(f" generate dense vector {dense_vector}")
    
    # Sparse Vector (Understands exact match for "Aspirin 75mg" or "ICD-10 Z71.3")
    sparse_result = list(sparse_model.embed([question]))[0]
    sparse_indices = sparse_result.indices.tolist()
    sparse_values = sparse_result.values.tolist()
    #print(f"generate sparse_values {sparse_values}")

    # ---------------------------------------------------------
    # 3. HYBRID SEARCH EXECUTION (Reciprocal Rank Fusion)
    # ---------------------------------------------------------
    # Using Qdrant's query_points to execute both searches concurrently
    # and fuse the results to get a broad top-10 candidate set.
    search_results = qdrant_client.query_points(
        collection_name="medibot_documents",
        prefetch=[
            # Branch A: Semantic Search
            Prefetch(
                query=dense_vector,
                using="dense",
                filter=rbac_filter,
                limit=10,
            ),
            # Branch B: Exact Keyword Search
            Prefetch(
                query={"indices": sparse_indices, "values": sparse_values},
                using="sparse",
                filter=rbac_filter,
                limit=10,
            )
        ],
        query=dense_vector, # Fallback scoring vector
        using="dense",
        limit=10 # Return the top 10 fused results for the reranker
    )

    # ---------------------------------------------------------
    # 4. FORMAT RESULTS FOR STATE
    # ---------------------------------------------------------
    retrieved_chunks = []
    for point in search_results.points:
        retrieved_chunks.append({
            "text": point.payload.get("text", ""),
            "source_document": point.payload.get("source_document", "Unknown Source"),
            "section_title": point.payload.get("section_title", "Unknown Section"),
            "collection": point.payload.get("collection", "Unknown Collection"),
            "score": point.score # Useful for debugging hybrid weights
        })

    print(f"✅ Retrieved {len(retrieved_chunks)} chunks securely.")
    
    # Update the LangGraph State
    return {"retrieved_chunks": retrieved_chunks}