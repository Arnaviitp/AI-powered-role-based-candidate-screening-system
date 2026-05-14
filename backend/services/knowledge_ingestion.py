"""
Knowledge ingestion service.

Loads role-specific documents, chunks them, generates embeddings,
and stores them in a ChromaDB vector database.
"""

import os
import re
import hashlib
from pathlib import Path
import fitz  # PyMuPDF
import chromadb
from chromadb.config import Settings as ChromaSettings

from config import KNOWLEDGE_BASE_DIR, CHROMA_PERSIST_DIR, CHUNK_SIZE, CHUNK_OVERLAP

# ── ChromaDB client (singleton) ──────────────────────────────────────
_chroma_client = None


def get_chroma_client() -> chromadb.ClientAPI:
    """Return a persistent ChromaDB client (singleton)."""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


def get_or_create_collection(role: str) -> chromadb.Collection:
    """Get or create a ChromaDB collection named after the normalised role."""
    client = get_chroma_client()
    collection_name = _normalise_collection_name(role)
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


# ── Text extraction ─────────────────────────────────────────────────

def extract_text_from_pdf(path: str) -> str:
    doc = fitz.open(path)
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n\n".join(pages)


def extract_text_from_file(path: str) -> str:
    ext = Path(path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(path)
    return Path(path).read_text(encoding="utf-8", errors="ignore")


# ── Chunking ─────────────────────────────────────────────────────────

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE,
               overlap: int = CHUNK_OVERLAP) -> list[str]:
    """
    Split text into overlapping chunks.
    Strategy: split on paragraph boundaries first, then merge paragraphs
    into chunks that respect `chunk_size` while preserving context.
    """
    # Split on double newlines (paragraph boundaries)
    paragraphs = re.split(r"\n{2,}", text)
    paragraphs = [p.strip() for p in paragraphs if p.strip()]

    chunks: list[str] = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= chunk_size:
            current_chunk += ("\n\n" + para if current_chunk else para)
        else:
            if current_chunk:
                chunks.append(current_chunk)
            # Start new chunk with overlap from end of previous chunk
            if overlap > 0 and current_chunk:
                tail = current_chunk[-overlap:]
                current_chunk = tail + "\n\n" + para
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    # Handle very long paragraphs that exceed chunk_size
    final_chunks: list[str] = []
    for chunk in chunks:
        if len(chunk) <= chunk_size * 1.5:
            final_chunks.append(chunk)
        else:
            # Force split on sentence boundaries
            sentences = re.split(r"(?<=[.!?])\s+", chunk)
            sub_chunk = ""
            for sent in sentences:
                if len(sub_chunk) + len(sent) + 1 <= chunk_size:
                    sub_chunk += (" " + sent if sub_chunk else sent)
                else:
                    if sub_chunk:
                        final_chunks.append(sub_chunk)
                    sub_chunk = sent
            if sub_chunk:
                final_chunks.append(sub_chunk)

    return final_chunks


# ── Ingestion pipeline ───────────────────────────────────────────────

def _normalise_collection_name(role: str) -> str:
    """Turn a role name into a valid ChromaDB collection name."""
    name = re.sub(r"[^a-zA-Z0-9]", "_", role.lower()).strip("_")
    if not name:
        return "general"
    # ChromaDB requires 3-63 chars, must start/end with alphanumeric
    name = name[:63]
    if not name[0].isalnum():
        name = "c" + name
    if not name[-1].isalnum():
        name = name + "0"
    return name


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()[:12]


def ingest_documents_for_role(role: str, file_paths: list[str] | None = None) -> dict:
    """
    Ingest documents for a given role into ChromaDB.
    If file_paths is None, scans the knowledge_base directory.
    Returns stats about the ingestion.
    """
    if file_paths is None:
        # Auto-discover from knowledge_base dir
        role_dir = KNOWLEDGE_BASE_DIR / _normalise_collection_name(role)
        if not role_dir.exists():
            # Try the general knowledge_base dir
            role_dir = KNOWLEDGE_BASE_DIR
        file_paths = [
            str(p) for p in role_dir.iterdir()
            if p.suffix.lower() in (".pdf", ".txt", ".md")
        ]

    if not file_paths:
        return {"status": "no_documents", "chunks_added": 0}

    collection = get_or_create_collection(role)
    total_chunks = 0

    for fpath in file_paths:
        fname = Path(fpath).name
        text = extract_text_from_file(fpath)
        chunks = chunk_text(text)

        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{_content_hash(fname)}_{i}"
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append({
                "source": fname,
                "chunk_index": i,
                "role": role,
            })

        if ids:
            # Upsert to handle re-ingestion gracefully
            collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            total_chunks += len(ids)

    return {
        "status": "success",
        "role": role,
        "files_processed": len(file_paths),
        "chunks_added": total_chunks,
        "collection_name": _normalise_collection_name(role),
    }


def query_knowledge_base(role: str, query_texts: list[str],
                          n_results: int = 5) -> list[dict]:
    """
    Query the knowledge base for the given role.
    Returns a list of relevant chunks with metadata.
    """
    try:
        collection = get_or_create_collection(role)

        # Check if collection has any documents
        if collection.count() == 0:
            return []

        results = collection.query(
            query_texts=query_texts,
            n_results=min(n_results, collection.count()),
        )
    except Exception:
        return []

    retrieved = []
    if results and results["documents"]:
        for docs, metas, distances in zip(
            results["documents"], results["metadatas"], results["distances"]
        ):
            for doc, meta, dist in zip(docs, metas, distances):
                retrieved.append({
                    "content": doc,
                    "source": meta.get("source", "unknown"),
                    "role": meta.get("role", role),
                    "relevance_score": 1 - dist,  # cosine distance → similarity
                })

    return retrieved


def ensure_knowledge_base_ready(role: str) -> bool:
    """Check if the knowledge base for a role has been ingested."""
    collection = get_or_create_collection(role)
    if collection.count() > 0:
        return True
    # Try auto-ingestion
    result = ingest_documents_for_role(role)
    return result.get("chunks_added", 0) > 0
