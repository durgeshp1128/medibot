from sql_rag import _call_llm
from sql_rag import sql_rag_chain
from retrieval import hybrid_retriever
import os
from dotenv import load_dotenv

load_dotenv()

        
    
def process_chat(message: dict, user: dict) -> dict:
    """Process a chat message and generate a structured response.

    Returns a dict containing:
        - answer: LLM generated answer string
        - sources: list of source metadata dicts
        - retrieval_type: "sql_rag" or "hybrid_rag"
        - role: the user's role
    """
    # Extract question from payload (support both "question" and "message")
    user_msg = message.get("question") or message.get("message") or ""
    user_msg = user_msg.strip()
    if not user_msg:
        return {"answer": "I didn't receive any question.", "sources": [], "retrieval_type": "none", "role": user.get("role", "")}

    role = user.get("role", "")

    # Helper to detect analytical / numeric queries
    def is_analytical(text: str) -> bool:
        num_keywords = ["average", "sum", "total", "count", "percentage", "ratio", "max", "min", "median"]
        if any(kw in text.lower() for kw in num_keywords):
            return True
        if any(ch.isdigit() for ch in text) and any(word in text.lower() for word in ["select", "where", "order", "group"]):
            return True
        return False

    # ---------- Analytical path (SQL RAG) ----------
    if is_analytical(user_msg) and role in {"admin", "billing_executive"}:
        answer = sql_rag_chain(user_msg, role)
        return {
            "answer": answer,
            "sources": [],
            "retrieval_type": "sql_rag",
            "role": role,
        }
    else: 
        # ---------- Non‑analytical path (Hybrid Retrieval) ----------
        candidates = hybrid_retriever(user_msg, role, top_k=10)
        if not candidates:
            return {"answer": "I couldn't find relevant information.", "sources": [], "retrieval_type": "hybrid_rag", "role": role}

        # Simple reranking: take top 3 by score
        top_candidates = sorted(candidates, key=lambda x: x.get("score", 0), reverse=True)[:3]
        # Build combined context for LLM
        context_texts = [c.get("text", "") for c in top_candidates]
        combined_context = "\n---\n".join(context_texts)

        # Gather source metadata for response
        sources = []
        for c in top_candidates:
            md = c.get("metadata", {})
            sources.append({
                "source_document": md.get("source_document"),
                "section_title": md.get("section_title"),
                "collection": md.get("collection"),
            })

    # Generate answer with LLM, citing sources implicitly via context
    prompt = (
        f"You are a helpful medical assistant. Answer the user's question using the provided context. "
        f"Cite sources by mentioning the document titles present in the context.\n\n"
        f"Context:\n{combined_context}\n\nQuestion: {user_msg}\nAnswer:"
    )
    answer = _call_llm(prompt)
    return {
        "answer": answer,
        "sources": sources,
        "retrieval_type": "hybrid_rag",
        "role": role,
    }
