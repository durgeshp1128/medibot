import os
from typing import List, Dict, Any
from sentence_transformers import CrossEncoder
from backend.app.graph.state import AgentState

# Load a cross‑encoder reranker model. Adjust name if you prefer a different model.
CROSS_ENCODER_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
reranker = CrossEncoder(CROSS_ENCODER_MODEL)

def rerank_node(state: AgentState) -> AgentState:
    """Rerank retrieved chunks using a cross‑encoder.
    Expects `state["retrieved_chunks"]` to be a list of dicts with a ``text`` field.
    Returns top‑N chunks (default 3) sorted by relevance score.
    """
    chunks = state.get("retrieved_chunks", [])
    question = state.get("question", "")
    if not chunks:
        return state
    # Prepare pairs for the cross‑encoder: (question, chunk_text)
    pairs = [(question, chunk.get("text", "")) for chunk in chunks]
    scores = reranker.predict(pairs)
    # Attach scores to chunks
    for chunk, score in zip(chunks, scores):
        chunk["rerank_score"] = float(score)
    # Sort by score descending and keep top 3
    top_chunks = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)[:3]
    state["retrieved_chunks"] = top_chunks
    return state