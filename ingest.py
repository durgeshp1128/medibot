import os
import json
from pathlib import Path
from typing import List, Dict, Any

from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance
from pypdf import PdfReader

# Load environment variables (optional)
from dotenv import load_dotenv
load_dotenv()

# Use Qdrant local storage (no external server needed)
QDRANT_LOCAL_PATH = os.getenv("QDRANT_LOCAL_PATH", "./qdrant_storage")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "medibot_chunks")

EMBEDDING_MODEL_NAME = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
embedder = SentenceTransformer(EMBEDDING_MODEL_NAME)

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
    Uses Docling's HybridChunker; if unavailable/fails, falls back to simple PyPDF text extraction.
    """
    folder_name = document_path.parent.name
    info = get_role_info(folder_name)
    collection_name = info["collection"]
    access_roles = info["access_roles"]
    
    # Try Docling and HybridChunker first
    try:
        converter = DocumentConverter()
        conversion_result = converter.convert(str(document_path))
        doc = conversion_result.document

        chunker = HybridChunker(
            tokenizer=EMBEDDING_MODEL_NAME,
            max_tokens=256
        )
        doc_chunks = list(chunker.chunk(doc))
        
        chunks: List[Dict[str, Any]] = []
        for chunk in doc_chunks:
            headings = []
            if hasattr(chunk, "meta") and chunk.meta is not None:
                headings = getattr(chunk.meta, "headings", []) or []
            
            # Format chunk text by prepending parent section headings as context
            if headings:
                context_prefix = " > ".join(headings)
                chunk_text = f"Context: {context_prefix}\n\n{chunk.text}"
                section_title = headings[-1]
            else:
                chunk_text = chunk.text
                section_title = "Document"
                
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    "source_document": document_path.name,
                    "collection": collection_name,
                    "access_roles": access_roles,
                    "section_title": section_title,
                    "chunk_type": "text"
                }
            })
        return chunks
    except Exception as e:
        print(f"Docling parsing failed for {document_path}: {e}. Falling back...")
        # Fallback for PDFs using PyPDF
        if document_path.suffix.lower() == ".pdf":
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
        raise NotImplementedError(f"Unsupported file type for fallback: {document_path.suffix}")

def embed_chunks(chunks: List[Dict[str, Any]], start_id: int) -> List[PointStruct]:
    """Generate real embeddings using SentenceTransformer and build Qdrant points."""
    points = []
    if not chunks:
        return points
        
    texts_to_embed = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode(texts_to_embed, show_progress_bar=False).tolist()
    
    for idx, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        payload = chunk["metadata"].copy()
        payload["text"] = chunk["text"]
        points.append(PointStruct(id=start_id + idx, vector=embedding, payload=payload))
    return points

def ensure_collection(client: QdrantClient):
    vector_size = embedder.get_sentence_embedding_dimension()
    # Recreate the collection if it exists but the vector size does not match
    if client.collection_exists(COLLECTION_NAME):
        info = client.get_collection(COLLECTION_NAME)
        current_size = info.config.params.vectors.size
        if current_size != vector_size:
            print(f"Deleting collection {COLLECTION_NAME} because its vector size {current_size} doesn't match model size {vector_size}")
            client.delete_collection(COLLECTION_NAME)
            
    if not client.collection_exists(COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
        )
        print(f"Created Qdrant collection {COLLECTION_NAME} with vector size {vector_size}")
    else:
        print(f"Qdrant collection {COLLECTION_NAME} already exists")

def ingest_data(data_root: Path):
    client = QdrantClient(path=QDRANT_LOCAL_PATH)
    ensure_collection(client)
    all_points: List[PointStruct] = []
    
    # Track point IDs globally across all documents to prevent overwriting
    current_id = 0
    
    # Process both PDF and Markdown documents
    for ext in ("*.pdf"):
        for file_path in data_root.rglob(ext):
            try:
                if not file_path.is_file():
                    continue
                print(f"Processing {file_path}")
                chunks = hierarchical_chunk(file_path)
                points = embed_chunks(chunks, current_id)
                all_points.extend(points)
                current_id += len(points)
            except PermissionError as perm_err:
                print(f"Skipping {file_path} due to permission error: {perm_err}")
                continue
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
                
    print(f"Total points generated: {len(all_points)}")
    batch_size = 100
    for i in range(0, len(all_points), batch_size):
        batch = all_points[i:i+batch_size]
        client.upsert(collection_name=COLLECTION_NAME, points=batch)
        print(f"Upserted {len(batch)} points (total {i+len(batch)})")
    print("Ingestion complete.")

if __name__ == "__main__":
    DATA_ROOT = Path(__file__).parent / "data" / "source_documents"
    ingest_data(DATA_ROOT)
