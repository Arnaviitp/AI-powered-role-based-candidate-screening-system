"""
Session management router.

Handles creating interview sessions, listing sessions, and session status.
"""

import shutil
import time
import logging
import re
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import Session, Question
from config import UPLOAD_DIR, SUPPORTED_ROLES, QUESTIONS_PER_SESSION
from services.resume_parser import parse_resume
from services.knowledge_ingestion import ensure_knowledge_base_ready
from services.rag_pipeline import retrieve_context, format_context_for_prompt
from services.question_generator import generate_questions

router = APIRouter(prefix="/api/sessions", tags=["Sessions"])
logger = logging.getLogger(__name__)


def _safe_upload_stem(candidate_name: str) -> str:
    stem = re.sub(r"[^a-zA-Z0-9_-]+", "_", candidate_name or "candidate").strip("_")
    return stem[:60] or "candidate"


def _safe_extension(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "pdf"
    if ext not in {"pdf", "txt", "text", "md"}:
        raise HTTPException(status_code=400, detail="Only PDF and text resumes are supported.")
    return "txt" if ext in {"text", "md"} else ext


@router.post("")
async def create_session(
    resume: UploadFile = File(...),
    role: str = Form(...),
    candidate_name: str = Form(""),
    db: DBSession = Depends(get_db),
):
    """
    Create a new interview session.
    1. Upload & parse resume
    2. Retrieve relevant knowledge base context
    3. Generate initial batch of questions
    4. Return session details
    """
    # Validate role
    if role not in SUPPORTED_ROLES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Supported roles: {SUPPORTED_ROLES}",
        )

    file_ext = _safe_extension(resume.filename or "")
    safe_name = _safe_upload_stem(candidate_name)
    file_path = UPLOAD_DIR / f"{safe_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{file_ext}"
    with open(file_path, "wb") as f:
        shutil.copyfileobj(resume.file, f)

    # Parse resume
    try:
        t0 = time.time()
        print(f"[Session] [1/4] Parsing resume...")
        parsed = parse_resume(str(file_path))
        print(f"[Session] OK: Resume parsed in {time.time()-t0:.1f}s")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Failed to parse resume: {str(e)}")

    # Create session
    session = Session(
        candidate_name=candidate_name or "Anonymous",
        role=role,
        resume_text=parsed["raw_text"],
        resume_filename=resume.filename,
        extracted_skills=parsed["skills"],
        extracted_technologies=parsed["technologies"],
        extracted_experience=parsed["experience_summary"],
        total_questions=QUESTIONS_PER_SESSION,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Ensure knowledge base is ready
    t1 = time.time()
    print(f"[Session] [2/4] Ensuring knowledge base ready for '{role}'...")
    try:
        kb_ready = ensure_knowledge_base_ready(role)
        print(f"[Session] OK: Knowledge base ready in {time.time()-t1:.1f}s")
    except Exception as e:
        kb_ready = False
        logger.warning("Knowledge base unavailable for %s: %s", role, e)
        print(f"[Session] WARN: Knowledge base unavailable after {time.time()-t1:.1f}s")

    # Retrieve context using RAG pipeline
    t2 = time.time()
    print(f"[Session] [3/4] RAG retrieval...")
    try:
        retrieved_chunks = retrieve_context(
            role=role,
            skills=parsed["skills"],
            technologies=parsed["technologies"],
            experience=parsed["experience_summary"],
        )
    except Exception as e:
        retrieved_chunks = []
        logger.warning("RAG retrieval failed for %s: %s", role, e)
    context = format_context_for_prompt(retrieved_chunks)
    print(f"[Session] OK: RAG retrieval done in {time.time()-t2:.1f}s ({len(retrieved_chunks)} chunks)")

    # Generate initial questions
    t3 = time.time()
    print(f"[Session] [4/4] Generating {QUESTIONS_PER_SESSION} questions via Gemini...")
    questions_data = generate_questions(
        role=role,
        skills=parsed["skills"],
        technologies=parsed["technologies"],
        experience_summary=parsed["experience_summary"],
        context=context,
        num_questions=QUESTIONS_PER_SESSION,
    )
    print(f"[Session] OK: Questions generated in {time.time()-t3:.1f}s")

    # Store questions in DB
    for i, qdata in enumerate(questions_data):
        q = Question(
            session_id=session.id,
            order_index=i,
            question_text=qdata["question"],
            topic=qdata.get("topic", "General"),
            difficulty=qdata.get("difficulty", "medium"),
            context_used=qdata.get("context_used", ""),
        )
        db.add(q)
    db.commit()

    return {
        "session_id": session.id,
        "candidate_name": session.candidate_name,
        "role": session.role,
        "extracted_skills": parsed["skills"],
        "extracted_technologies": parsed["technologies"],
        "total_questions": QUESTIONS_PER_SESSION,
        "knowledge_base_ready": kb_ready,
        "status": "active",
    }


@router.get("")
async def list_sessions(db: DBSession = Depends(get_db)):
    """List all interview sessions."""
    sessions = db.query(Session).order_by(Session.created_at.desc()).all()
    return [s.to_dict() for s in sessions]


@router.get("/{session_id}")
async def get_session(session_id: str, db: DBSession = Depends(get_db)):
    """Get details for a specific session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions = [q.to_dict() for q in session.questions]
    return {
        **session.to_dict(),
        "questions": questions,
    }


@router.delete("/{session_id}")
async def delete_session(session_id: str, db: DBSession = Depends(get_db)):
    """Delete a session and all its questions."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.delete(session)
    db.commit()
    return {"status": "deleted", "session_id": session_id}
