import os
import sys
from typing import List, Dict, Any
from pathlib import Path

# Document Parsing & Chunking
from docling.document_converter import DocumentConverter
from docling.chunking import HybridChunker
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption

# Fallback imports for docling core components to be compatible with different versions
try:
    from docling_core.transforms.chunker.hierarchical_chunker import (
        ChunkingDocSerializer,
        ChunkingSerializerProvider,
    )
except ImportError:
    from docling.chunking import ChunkingDocSerializer, ChunkingSerializerProvider

try:
    from docling_core.transforms.serializer.markdown import MarkdownTableSerializer
except ImportError:
    from docling.serializer.markdown import MarkdownTableSerializer

# Vector Store Client
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, SparseVectorParams, PointStruct, SparseVector

# Embedding Model (Dense)
from sentence_transformers import SentenceTransformer
# Embedding Model (Sparse)
from fastembed import SparseTextEmbedding

# LangChain Framework Integrations
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore, FastEmbedSparse, RetrievalMode

# 1. Configuration & Security Access Matrix
COLLECTION_ACCESS_MAP = {
    "general": ["doctor", "nurse", "billing_executive", "technician", "admin"],
    "clinical": ["doctor", "admin"],
    "nursing": ["nurse", "doctor", "admin"],
    "billing": ["billing_executive", "admin"],
    "equipment": ["technician", "admin"]
}

class MDTableSerializerProvider(ChunkingSerializerProvider):
    """Custom serializer provider that uses MarkdownTableSerializer to format tables."""
    def get_serializer(self, doc):
        return ChunkingDocSerializer(
            doc=doc,
            table_serializer=MarkdownTableSerializer()
        )

class FlattenedQdrantVectorStore(QdrantVectorStore):
    """Custom QdrantVectorStore that flattens metadata to the root level of the payload."""
    @classmethod
    def _build_payloads(
        cls,
        texts: List[str],
        metadatas: List[dict] | None,
        content_payload_key: str,
        metadata_payload_key: str,
    ) -> List[dict]:
        payloads = []
        for i, text in enumerate(texts):
            if text is None:
                raise ValueError("At least one of the texts is None.")
            metadata = metadatas[i] if metadatas is not None else {}
            payload = {
                content_payload_key: text,
                **metadata
            }
            payloads.append(payload)
        return payloads

class MediBotIngestor:
    def __init__(self, qdrant_url: str = "../data/qdrant_storage", dense_model_name: str = "all-MiniLM-L6-v2", sparse_model_name: str = "Qdrant/bm25"):
        """Initializes the ingestion pipeline with Docling, LangChain, and Qdrant."""
        # Configure pipeline options to disable OCR to avoid std::bad_alloc on complex pages
        pipeline_options = PdfPipelineOptions()
        pipeline_options.do_ocr = False
        
        self.converter = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
        # Initialize LangChain Dense Embeddings (SentenceTransformers wrapper)
        self.dense_model = HuggingFaceEmbeddings(
            model_name=dense_model_name,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )

        self.embedder = SentenceTransformer(dense_model_name)
        # Configure max sequence length on the underlying SentenceTransformer
        # self.dense_model.client.max_seq_length = 512
        
        # Initialize LangChain Sparse Embeddings (FastEmbed wrapper)
        self.sparse_model = FastEmbedSparse(model_name=sparse_model_name, batch_size=32)
        
        # Initialize Native Qdrant client (for collection checks and manual schema setup)
        self.qdrant_client = QdrantClient(path=qdrant_url)
        self.vector_size = self.embedder.get_embedding_dimension()

        
    def setup_qdrant_collection(self, collection_name: str):
        """Creates a Qdrant collection with both dense and sparse configurations, recreating if it has old configuration."""
        if self.qdrant_client.collection_exists(collection_name):
            print(f"🗑️ Recreating collection '{collection_name}' to ensure correct named vector configuration...")
            self.qdrant_client.delete_collection(collection_name)
            
        self.qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config={
                "dense": VectorParams(size=self.vector_size, distance=Distance.COSINE)
            },
            sparse_vectors_config={
                "sparse": SparseVectorParams()
            }
        )
        print(f"✅ Created Qdrant collection: {collection_name} with named 'dense' and 'sparse' vectors.")

    def parse_and_chunk_document(self, file_path: Path, collection_type: str) -> List[Dict[str, Any]]:
        """
        Parses a document using Docling, extracts hierarchical headings as structural context, 
        and builds chunks compliant with the required metadata schema using HybridChunker.
        """
        if collection_type not in COLLECTION_ACCESS_MAP:
            raise ValueError(f"Unknown collection type: {collection_type}")

        print(f"📄 Parsing {file_path.name} via Docling...")
        # Step A: Structural Aware Parsing
        result = self.converter.convert(file_path)
        doc = result.document
        
        # Step B: Initialize Chunker with tokenizer matching SentenceTransformer and custom markdown serializer
        chunker = HybridChunker(
            tokenizer="sentence-transformers/all-MiniLM-L6-v2",
            max_tokens=384,  # Token-aware size limit
            serializer_provider=MDTableSerializerProvider()
        )
        
        chunks = []
        # Step C: Hierarchical Node Processing
        chunk_iter = chunker.chunk(dl_doc=doc)
        
        for chunk in chunk_iter:
            # Extract parent section heading
            headings = chunk.meta.headings if hasattr(chunk.meta, "headings") and chunk.meta.headings else []
            parent_heading = headings[-1] if headings else "General Context"
            
            # Contextualized text - use docling's contextualize to capture rich Markdown structure (tables/code)
            serialized_text = chunker.contextualize(chunk=chunk)
            
            # Embed parent heading as context within the text body
            # Each chunk's embedded text must carry its parent section heading as context
            enriched_text = f"Section: {parent_heading}\nContent: {serialized_text}"
            
            # Determine chunk type
            chunk_type = "text"
            if hasattr(chunk.meta, "doc_items") and chunk.meta.doc_items:
                for item in chunk.meta.doc_items:
                    label_str = str(item.label).lower()
                    if "table" in label_str:
                        chunk_type = "table"
                        break
                    elif "code" in label_str:
                        chunk_type = "code"
                        break
            
            metadata = {
                "source_document": file_path.name,
                "collection": collection_type,
                "access_roles": COLLECTION_ACCESS_MAP[collection_type],
                "section_title": parent_heading,
                "chunk_type": chunk_type
            }
            
            chunks.append({
                "text": enriched_text,
                "metadata": metadata
            })
            
        return chunks

    def upload_to_vector_store(self, qdrant_collection: str, chunks: List[Dict[str, Any]]):
        """Generates embeddings and uploads documents to Qdrant collection using the LangChain framework."""
        # 1. Setup/recreate the collection structure manually to guarantee named vectors ('dense' and 'sparse')
        self.setup_qdrant_collection(qdrant_collection)
        
        # 2. Convert chunks to LangChain Document objects with tokenizer-based truncation
        tokenizer = getattr(self.dense_model, "client", getattr(self.dense_model, "_client", None)).tokenizer
        documents = []
        for chunk in chunks:
            # Truncate text to 512 tokens to avoid Splade sequence length limit errors
            encoded = tokenizer(chunk["text"], max_length=512, truncation=True, add_special_tokens=False)
            truncated_text = tokenizer.decode(encoded["input_ids"])

            doc = Document(
                page_content=truncated_text,
                metadata=chunk["metadata"]
            )
            documents.append(doc)
            
        # 3. Instantiate our custom Qdrant vector store wrapper
        vector_store = FlattenedQdrantVectorStore(
            client=self.qdrant_client,
            collection_name=qdrant_collection,
            embedding=self.dense_model,
            sparse_embedding=self.sparse_model,
            retrieval_mode=RetrievalMode.HYBRID,
            content_payload_key="text",
            vector_name="dense",
            sparse_vector_name="sparse"
        )
        
        # 4. Upload documents via LangChain vector store in batches to reduce I/O pressure
        batch_size = 64
        total = len(documents)
        print(f"📤 Uploading {total} documents to Qdrant collection '{qdrant_collection}' via LangChain in batches of {batch_size}...")
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            vector_store.add_documents(batch)
        print(f"🚀 Successfully indexed {total} documents into '{qdrant_collection}' using LangChain with RBAC configurations.")
        # Ensure Qdrant client is closed to flush writes
        self.qdrant_client.close()

# --- Execution Entry Point ---
if __name__ == "__main__":
    # import argparse
    # parser = argparse.ArgumentParser(description="MediBot Document Ingestion Engine")
    # parser.add_argument("--qdrant-url", default=os.getenv("QDRANT_URL", "http://localhost:6333"), help="Qdrant connection URL")
    # args = parser.parse_args()
    base_path_data = Path(__file__).resolve().parent.parent.parent / "data"
    ingestor = MediBotIngestor(base_path_data / "qdrant_storage")
    
    # Target directory structure: backend/data/<collection_type>/<files>
    base_data_dir = base_path_data / "medibot_docs"
    if not base_data_dir.exists():
        base_data_dir = Path("backend/data/medibot_docs")
        
    if not base_data_dir.exists():
        print(f"❌ Data directory not found at {base_data_dir.resolve()}")
        sys.exit(1)
        
    print(f"📂 Scanning data directory: {base_data_dir.resolve()}")
    all_chunks = []
    
    for collection_type in COLLECTION_ACCESS_MAP.keys():
        dir_path = base_data_dir / collection_type
        if not dir_path.exists() or not dir_path.is_dir():
            print(f"⚠️ Collection directory {dir_path} does not exist. Skipping.")
            continue
            
        print(f"📁 Scanning collection directory: {collection_type}")
        # Find PDF and Markdown files
        files = list(dir_path.glob("*.pdf"))
        for file_path in files:
            try:
                 
                chunks = ingestor.parse_and_chunk_document(file_path, collection_type)
                all_chunks.extend(chunks)
                print(f"   Processed {file_path.name}: Generated {len(chunks)} chunks.")
                
            except Exception as e:
                print(f"   ❌ Error processing {file_path.name}: {e}")
                
    if all_chunks:
        print(f"📤 Uploading {len(all_chunks)} total chunks to vector store...")
        ingestor.upload_to_vector_store(qdrant_collection="medibot_documents", chunks=all_chunks)
    else:
        print("⚠️ No chunks were generated. Nothing to upload.")