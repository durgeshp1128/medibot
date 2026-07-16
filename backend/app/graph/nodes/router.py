from typing import List, Dict, Any
import re
from fastapi import HTTPException
from backend.app.graph.state import AgentState

# Mapping from role to allowed collections
ROLE_COLLECTIONS = {
    "nurse": ["clinical", "general"],
    "doctor": ["nursing", "general"],
    "billing_executive": ["billing", "general"],
    "technician": ["equipment", "general"],
    "admin": ["clinical", "nursing", "billing", "equipment", "general"],
}

ANALYTICAL_KEYWORDS = [
    "how many",
    "total",    
    "average",
    "sum",
    "count",
    "percentage",
    "max",
    "min",
]

def router_node(state: AgentState) -> Dict[str, Any]:
    """Determine routing and allowed collections based on role and question.
    Updates:
        - route_decision: "sql_rag" or "hybrid_rag"
        - allowed_collections: list of collection strings
    """
    role = state.get("user_role")
    if not role:
        raise HTTPException(status_code=400, detail="user_role missing in state")
    # Determine allowed collections
    allowed = ROLE_COLLECTIONS.get(role, ["general"])
    state["allowed_collections"] = allowed

    question = state.get("question", "").lower()
    # Simple heuristic for analytical queries
    if any(keyword in question for keyword in ANALYTICAL_KEYWORDS):
        state["route_decision"] = "sql_rag"
    else:
        state["route_decision"] = "hybrid_rag"
    return state