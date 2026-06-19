import os
import json
from pathlib import Path
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# Load environment variables (optional)
from dotenv import load_dotenv
load_dotenv()

# Use Qdrant local storage (no external server needed)
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "./qdrant_storage")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "medibot_chunks")

# Role to collection mapping (based on assignment spec)
COLLECTION_ROLE_MAP = {
    "general": {
        "collection": "general",
        "access_roles": ["doctor", "nurse", "billing_executive", "technician", "admin"]
    },
    "clinical": {
        "collection": "clinical",
        "access_roles": ["doctor", "admin"]
    },
    "nursing": {
        "collection": "nursing",
        "access_roles": ["nurse", "doctor", "admin"]
    },
    "billing": {
        "collection": "billing",
        "access_roles": ["billing_executive", "admin"]
    },
    "equipment": {
        "collection": "equipment",
        "access_roles": ["technician", "admin"]
    },
}

def get_role_info(folder_name: str) -> Dict[str, Any]:
    """Return collection and access_roles for a given folder name. Defaults to 'general'."""
    return COLLECTION_ROLE_MAP.get(folder_name.lower(), COLLECTION_ROLE_MAP["general"])

def hierarchical_chunk(document_path: Path) -> List[Dict[str, Any]]:
    """Parse a PDF/Markdown file and return hierarchical chunks.
    Tries to use Docling; if unavailable, falls back to simple PyPDF text extraction.
    """
    folder_name = document_path.parent.name
    info = get_role_info(folder_name)
    collection_name = info["collection"]
    access_roles = info["access_roles"]
    # Try Docling first
    try:
        converter = DocumentConverter()
        conversion_result = converter.convert(str(document_path))
        doc = conversion_result.document
        chunks: List[Dict[str, Any]] = []
        def walk(node, parent_title=""):
            title = getattr(node, "title", parent_title) or parent_title
            if hasattr(node, "text") and node.text:
                chunks.append({
                    "text": node.text,
                    "metadata": {
                        "source_document": document_path.name,
                        "collection": collection_name,
                        "access_roles": access_roles,
                        "section_title": title,
                        "chunk_type": "text"
                    }
                })
            for child in getattr(node, "children", []):
                walk(child, title)
        walk(doc)
        return chunks
    except Exception as e:
        # Fallback for PDFs using PyPDF
        if document_path.suffix.lower() == ".pdf":
            from pypdf import PdfReader
            reader = PdfReader(str(document_path))
            chunks = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    chunks.append({
                        "text": text,
                        "metadata": {
                            "source_document": document_path.name,
                            "collection": collection_name,
                            "access_roles": access_roles,
                            "section_title": f"Page {i+1}",
                            "chunk_type": "text"
                        }
                    })
            return chunks
        # Fallback for markdown or other text files
        else:
            with open(document_path, "r", encoding="utf-8") as f:
                text = f.read()
            return [{
                "text": text,
                "metadata": {
                    "source_document": document_path.name,
                    "collection": collection_name,
                    "access_roles": access_roles,
                    "section_title": "Document",
                    "chunk_type": "text"
                }
            }]


def embed_chunks(chunks: List[Dict[str, Any]]) -> List[PointStruct]:
    """Generate placeholder embeddings (replace with real model later) and build Qdrant points."""
    points = []
    for idx, chunk in enumerate(chunks):
        embedding = [0.0] * 768  # placeholder
        payload = chunk["metadata"].copy()
        payload["text"] = chunk["text"]
        points.append(PointStruct(id=idx, vector=embedding, payload=payload))
    return points

def ensure_collection(client: QdrantClient):
    # Use collection_exists and create_collection to avoid deprecation
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=768, distance=Distance.COSINE)
        )
        print(f"Created Qdrant collection {COLLECTION_NAME}")
    else:
        print(f"Qdrant collection {COLLECTION_NAME} already exists")

def ingest_data(data_root: Path):
    client = QdrantClient(path=QDRANT_LOCAL_PATH)
    ensure_collection(client)
    all_points: List[PointStruct] = []
    # Define file patterns to ingest (add more as needed)
    for ext in ("*.pdf"):
        for file_path in data_root.rglob(ext):
            # Skip if not a regular file or if we lack permission
            try:
                if not file_path.is_file():
                    continue
                print(f"Processing {file_path}")
                chunks = hierarchical_chunk(file_path)
                points = embed_chunks(chunks)
                all_points.extend(points)
            except PermissionError as perm_err:
                print(f"Skipping {file_path} due to permission error: {perm_err}")
                continue
    # Upsert in batches to avoid overload
    batch_size = 5000
    for i in range(0, len(all_points), batch_size):
        batch = all_points[i:i+batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"Upserted {len(batch)} points (total {i+len(batch)})")
    print("Ingestion complete.")

if __name__ == "__main__":
    DATA_ROOT = Path(__file__).parent / "data"
    ingest_data(DATA_ROOT)
