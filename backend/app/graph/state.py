from typing import List, Dict, Any, TypedDict

class AgentState(TypedDict):
    """
    State definition for the MediBot LangGraph runtime.
    Preserves security, routing decisions, query parameters, 
    and output results across execution nodes.
    """
    question: str
    user_role: str
    allowed_collections: List[str]
    route_decision: str  # "sql_rag" or "hybrid_rag"
    retrieved_chunks: List[Dict[str, Any]]
    final_answer: str
    sources: List[Dict[str, str]]
    error: str