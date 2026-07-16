import sqlite3
import os
from typing import Dict, Any
from backend.app.graph.state import AgentState

# Simple SQL RAG implementation using SQLite

def sql_rag_chain(question: str) -> str:
    """Translate a natural language question to SQL, execute, and return answer.
    For demo purposes this uses a very naive keyword‑based mapping.
    """
    conn = sqlite3.connect(os.path.join(os.path.dirname(__file__), "../../data/mediassist.db"))
    cursor = conn.cursor()
    # Very simple heuristic: look for known intents
    lowered = question.lower()
    if "claims" in lowered and "count" in lowered:
        sql = "SELECT COUNT(*) FROM claims"
    elif "claims" in lowered and "total" in lowered:
        sql = "SELECT SUM(amount) FROM claims"
    elif "maintenance" in lowered and "open" in lowered:
        sql = "SELECT COUNT(*) FROM maintenance_tickets WHERE status = 'open'"
    else:
        return "I couldn't determine the appropriate SQL query for that question."
    try:
        cursor.execute(sql)
        result = cursor.fetchone()
        answer = f"Result: {result[0]}"
    except Exception as e:
        answer = f"SQL execution error: {e}"
    finally:
        conn.close()
    return answer

def sql_rag_node(state: AgentState) -> Dict[str, Any]:
    """LangGraph node that runs SQL RAG.
    Expects `state["question"]` and returns `final_answer`, `retrieval_type`.
    """
    question = state.get("question", "")
    answer = sql_rag_chain(question)
    state["final_answer"] = answer
    state["sources"] = []  # No document sources for SQL
    state["retrieval_type"] = "sql_rag"
    return state