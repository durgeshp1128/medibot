# rerank.py
"""Cross‑encoder reranking for retrieved chunks.

- Uses a Sentence‑Transformers cross‑encoder (default ``cross-encoder/ms-marco-MiniLM-L-6-v2``).
- Accepts the original query and a list of candidate dicts produced by ``retrieval.hybrid_retriever``.
- Returns the top‑k candidates ordered by relevance.
"""

import os
import json
from typing import List, Dict, Any

# Lazy‑load the cross‑encoder model
_cross_encoder = None

def _get_cross_encoder():
    global _cross_encoder
    if _cross_encoder is None:
        model_name = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
        from sentence_transformers import CrossEncoder
        _cross_encoder = CrossEncoder(model_name)
    return _cross_encoder


def rerank(query: str, candidates: List[Dict[str, Any]], top_k: int = 3) -> List[Dict[str, Any]]:
    """Rerank ``candidates`` using a cross‑encoder.

    Args:
        query: User question.
        candidates: Output of ``retrieval.hybrid_retriever`` – each entry must contain a ``text`` field.
        top_k: Number of top results to keep.
    Returns:
        A list of the best ``top_k`` candidate dicts, preserving the original ``metadata``.
    """
    if not candidates:
        return []
    model = _get_cross_encoder()
    # Prepare (query, candidate_text) pairs for the model
    pairs = [(query, cand["text"]) for cand in candidates]
    scores = model.predict(pairs)  # higher = more relevant
    # Attach scores, sort, and trim
    for cand, score in zip(candidates, scores):
        cand["_score"] = float(score)
    ranked = sorted(candidates, key=lambda c: c["_score"], reverse=True)[:top_k]
    # Clean up temporary field before returning
    for cand in ranked:
        cand.pop("_score", None)
    return ranked

if __name__ == "__main__":
    # Simple demo with dummy data
    demo_query = "What dosage of amoxicillin is recommended for a child?"
    demo_candidates = [
        {"text": "Amoxicillin 250 mg twice daily for children under 12 years.", "metadata": {"source_document": "clinical.pdf", "section_title": "Amoxicillin Dosage", "collection": "clinical", "access_roles": ["doctor", "admin"]}},
        {"text": "General antibiotic guidelines.", "metadata": {"source_document": "general.pdf", "section_title": "Antibiotics", "collection": "general", "access_roles": ["doctor", "nurse", "admin"]}},
        {"text": "Amoxicillin contraindicated for penicillin‑allergic patients.", "metadata": {"source_document": "safety.pdf", "section_title": "Contraindications", "collection": "clinical", "access_roles": ["doctor", "admin"]}},
    ]
    top = rerank(demo_query, demo_candidates, top_k=2)
    print(json.dumps(top, indent=2, ensure_ascii=False))
