# medibot
**MediBot** is an enterprise-grade intelligent assistant built for **MediAssist Health Network** to streamline knowledge discovery across 12 hospitals and 40+ clinics in India. It indexes clinical guidelines, hospital policies, and equipment manuals while enforcing strict **Role-Based Access Control (RBAC)** at the database retrieval layer.

## Tech Stack

- **Framework**: FastAPI
- **Database**: Quadrant
- **RAG**: LangChain
- **Authentication**: JWT + OAuth2 Password Flow (planned)
- **UI**: React (planned)

## Getting Started

### Prerequisites

- Python 3.11+
- Requirements.txt

```
# Web framework & server
fastapi>=0.110.0
uvicorn>=0.28.0
python-multipart>=0.0.9

# Document Processing
docling>=1.0.0

# Vector DB & Embeddings
qdrant-client>=1.8.0
sentence-transformers>=2.6.0
cohere>=5.0.0             # Optional (if using cloud embeddings) or use HuggingFace open-source locally
openai>=1.14.0            # For Cloud LLM / Inference API (or Anthropic/Groq)

# Data processing & DB
pydantic>=2.6.0
pydantic-settings>=2.2.0
sqlalchemy>=2.0.0
```

### Installation

1. Clone the repository
```bash
git clone <repository-url>
cd medibot
```

2. Create virtual environment
```bash
python -m venv .venv

# Windows
.venv/Scripts/activate

# macOS/Linux
source .venv/bin/activate
```

3. Install dependencies
```bash
python -m pip install -r requirements.txt
```

## Project Structure

```
medibot-backend/
├── data/
│   ├── general/       # HR handbook, FAQs, etc.
│   ├── clinical/      # Treatment protocols
│   ├── nursing/       # Care guidelines
│   ├── billing/       # Insurance references
│   ├── equipment/     # Manuals & schedules
│   └── mediassist.db  # Provided SQLite DB
├── src/
│   ├── __init__.py
│   ├── config.py      # Environment variables & constants
│   ├── ingestion.py   # Docling + chunking script
│   ├── vector_db.py   # Qdrant client & Hybrid index configuration
│   ├── search.py      # Dense + BM25 + Cross-Encoder Reranker
│   ├── sql_rag.py     # SQL generation & execution chain
│   └── main.py        # FastAPI application routers
├── .env
└── requirements.txt
```

### Running the Server

```bash
uvicorn app.main:app --reload --port 8000
```

Access the API at `http://localhost:8000`
View interactive docs at `http://localhost:8000/docs`

