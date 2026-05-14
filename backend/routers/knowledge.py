"""
Knowledge base management router.

Allows uploading and ingesting documents into the vector store.
"""

import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from config import KNOWLEDGE_BASE_DIR
from services.knowledge_ingestion import (
    ingest_documents_for_role,
    get_or_create_collection,
    get_chroma_client,
)

router = APIRouter(prefix="/api/knowledge", tags=["Knowledge Base"])


@router.post("/upload")
async def upload_knowledge_document(
    file: UploadFile = File(...),
    role: str = Form(...),
):
    """Upload a document to the knowledge base for a specific role."""
    try:
        # Save file to knowledge_base directory
        role_dir = KNOWLEDGE_BASE_DIR / role.lower().replace("/", "_").replace(" ", "_")
        role_dir.mkdir(parents=True, exist_ok=True)

        file_path = role_dir / file.filename
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Ingest the document
        result = ingest_documents_for_role(role, [str(file_path)])
        return {
            "status": "success",
            "filename": file.filename,
            "role": role,
            **result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


@router.post("/ingest/{role}")
async def ingest_role_documents(role: str):
    """Trigger ingestion of all documents for a specific role."""
    try:
        result = ingest_documents_for_role(role)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/status")
async def knowledge_base_status():
    """Get the status of all knowledge base collections."""
    try:
        client = get_chroma_client()
        # ChromaDB >= 0.5.x: list_collections() may return names or objects
        # depending on version. Handle both gracefully.
        raw_collections = client.list_collections()
        status = []
        for col in raw_collections:
            try:
                # If col is already a Collection object
                if hasattr(col, "name") and hasattr(col, "count"):
                    status.append({
                        "name": col.name,
                        "document_count": col.count(),
                    })
                elif isinstance(col, str):
                    # col is just a name string; fetch the actual collection
                    collection = client.get_collection(col)
                    status.append({
                        "name": col,
                        "document_count": collection.count(),
                    })
                else:
                    # Fallback: try treating it as a name
                    name = str(col)
                    collection = client.get_collection(name)
                    status.append({
                        "name": name,
                        "document_count": collection.count(),
                    })
            except Exception:
                # Skip collections that can't be accessed
                status.append({
                    "name": str(col),
                    "document_count": -1,
                })
        return {"collections": status}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get status: {str(e)}")
