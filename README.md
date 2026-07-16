# medibot
**MediBot** is an enterprise-grade intelligent assistant built for **MediAssist Health Network** to streamline knowledge discovery across 12 hospitals and 40+ clinics in India. It indexes clinical guidelines, hospital policies, and equipment manuals while enforcing strict **Role-Based Access Control (RBAC)** at the database retrieval layer.

### Flow

flowchart TD
    Start([User Input: Query + Role]) --> InitNode[Node 1: Initialize & Enforce RBAC]
    InitNode --> RouteEdge{Conditional Edge: Router}
    
    RouteEdge -- "analytical" --> SQLAuth{Is Admin/Billing?}
    SQLAuth -- "Yes" --> GenSQL[Node 2A: Generate SQL]
    SQLAuth -- "No" --> BlockNode[Node 2B: Set RBAC Block Message]
    
    GenSQL --> ExecSQL[Node 3A: Execute SQL]
    ExecSQL --> FormatSQLAns[Node 4A: Synthesize Answer]
    
    RouteEdge -- "document" --> HybridRet[Node 2C: Hybrid Retrieval Qdrant + BM25]
    HybridRet --> RerankNode[Node 3C: Cross-Encoder Rerank]
    RerankNode --> LLMDocAns[Node 4C: Generate RAG Answer]
    
    FormatSQLAns --> End([Return Response])
    LLMDocAns --> End
    BlockNode --> End

### setup

cd backend
uv sync
source .venv/Scripts/activate
python -m backend.app.graph.workflow
