# medibot
**MediBot** is an enterprise-grade intelligent assistant built for **MediAssist Health Network** to streamline knowledge discovery across 12 hospitals and 40+ clinics in India. It indexes clinical guidelines, hospital policies, and equipment manuals while enforcing strict **Role-Based Access Control (RBAC)** at the database retrieval layer.

## Tech Stack

- **Framework**: FastAPI
- **Database**: Quadrant
- **RAG**: HyBrid RAG + SQL RAG
- **Authentication**: JWT + OAuth2 Password Flow (planned)
- **UI**: React (planned)


### Prerequisites

- Python 3.11+
- Requirements.txt

```
fastapi
uvicorn[standard]
qdrant-client
langchain
torch
sentence-transformers
rank_bm25
docling
pypdf
python-dotenv
pyjwt
sqlalchemy
pandas
python-jose
```

### Installation

1. Clone the repository
```bash
git clone https://github.com/your-org/medibot.git
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


### Running the Server

```bash
uvicorn main:app --reload --port 8000
```

Access the API at `http://localhost:8000`

### Running frontend

```
npm run dev

Access ui at http://localhost:5173/
```

### USAGE


Example Query

```
what is hospital policy for sick leave if fall ill in mid shift ?

```
Provide me detail report about total claim raised for cardiology department and how many of them are still in pending and how many of them are in rejected ?

```
show me internal diagnostic protocol that attending physicians are allowed to sign off.

```
