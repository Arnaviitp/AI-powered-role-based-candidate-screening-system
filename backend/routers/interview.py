"""
Interview interaction router.

Handles the question/answer flow during an active interview session.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session as DBSession

from database import get_db
from models import Session, Question
from services.question_generator import evaluate_answer, generate_session_summary
from services.rag_pipeline import retrieve_context, format_context_for_prompt
from services.question_generator import generate_questions

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/interview", tags=["Interview"])


class AnswerSubmission(BaseModel):
    answer: str


@router.get("/{session_id}/current-question")
async def get_current_question(session_id: str, db: DBSession = Depends(get_db)):
    """Get the current unanswered question for the session."""
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        return {
            "status": "completed",
            "message": "This interview session is already completed.",
            "session_id": session_id,
        }

    # Find the first unanswered question
    current_q = (
        db.query(Question)
        .filter(Question.session_id == session_id, Question.candidate_answer.is_(None))
        .order_by(Question.order_index)
        .first()
    )

    if not current_q:
        return {
            "status": "all_answered",
            "message": "All questions have been answered. Retrieve your summary.",
            "session_id": session_id,
        }

    # Count answered questions
    answered_count = (
        db.query(Question)
        .filter(Question.session_id == session_id, Question.candidate_answer.isnot(None))
        .count()
    )

    return {
        "status": "active",
        "question_id": current_q.id,
        "question_number": answered_count + 1,
        "total_questions": session.total_questions,
        "question_text": current_q.question_text,
        "topic": current_q.topic,
        "difficulty": current_q.difficulty,
    }


@router.post("/{session_id}/answer/{question_id}")
async def submit_answer(
    session_id: str,
    question_id: str,
    payload: AnswerSubmission,
    db: DBSession = Depends(get_db),
):
    """
    Submit an answer for a specific question.
    The system evaluates the answer and returns feedback.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    question = db.query(Question).filter(
        Question.id == question_id, Question.session_id == session_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    if question.candidate_answer is not None:
        raise HTTPException(status_code=400, detail="Question already answered")

    # Evaluate the answer
    try:
        evaluation = evaluate_answer(
            question=question.question_text,
            answer=payload.answer,
            role=session.role,
            context=question.context_used or "",
        )
    except Exception as e:
        logger.error(f"Answer evaluation failed: {e}")
        evaluation = {
            "score": 5.0,
            "feedback": "Answer recorded. Automated evaluation temporarily unavailable.",
        }

    # Update question record
    question.candidate_answer = payload.answer
    question.score = evaluation["score"]
    question.feedback = evaluation["feedback"]
    question.answered_at = datetime.now(timezone.utc)

    # Update session progress
    session.current_question_index += 1

    # Check if all questions answered — count BEFORE committing current answer
    total_unanswered = (
        db.query(Question)
        .filter(Question.session_id == session_id, Question.candidate_answer.is_(None))
        .count()
    )

    # current question is being answered now, so subtract 1
    is_complete = total_unanswered <= 1

    if is_complete:
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)

    db.commit()

    return {
        "question_id": question_id,
        "score": evaluation["score"],
        "feedback": evaluation["feedback"],
        "fallback": evaluation.get("fallback", False),
        "is_complete": is_complete,
        "questions_remaining": max(0, total_unanswered - 1),
    }


@router.get("/{session_id}/summary")
async def get_session_summary(session_id: str, db: DBSession = Depends(get_db)):
    """
    Generate and return a comprehensive summary of the interview session.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    questions = (
        db.query(Question)
        .filter(Question.session_id == session_id)
        .order_by(Question.order_index)
        .all()
    )

    # Build Q&A data for summary generation
    qa_data = []
    for q in questions:
        qa_data.append({
            "order": q.order_index + 1,
            "question": q.question_text,
            "answer": q.candidate_answer,
            "topic": q.topic,
            "difficulty": q.difficulty,
            "score": q.score,
            "feedback": q.feedback,
        })

    # Generate AI summary
    try:
        summary_data = generate_session_summary(
            role=session.role,
            skills=session.extracted_skills or [],
            questions_and_answers=qa_data,
        )
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        scores = [qa.get("score", 5) for qa in qa_data if qa.get("score")]
        avg = sum(scores) / len(scores) if scores else 5.0
        summary_data = {
            "overall_score": round(avg, 1),
            "summary": "Interview completed. Please review individual responses.",
            "strengths": ["Completed all questions"],
            "improvements": ["Review needed"],
            "recommendation": "Maybe",
            "topic_scores": {},
        }

    # Update session with summary
    session.overall_score = summary_data.get("overall_score", 0)
    session.summary = summary_data.get("summary", "")
    if session.status != "completed":
        session.status = "completed"
        session.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "session_id": session_id,
        "candidate_name": session.candidate_name,
        "role": session.role,
        "extracted_skills": session.extracted_skills,
        **summary_data,
        "questions": qa_data,
    }


@router.post("/{session_id}/generate-more-questions")
async def generate_more_questions(
    session_id: str,
    db: DBSession = Depends(get_db),
):
    """
    Generate additional adaptive questions based on previous performance.
    This allows the interview to adapt in real-time.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Cannot add questions to a completed session")

    # Get previous Q&A
    prev_questions = (
        db.query(Question)
        .filter(Question.session_id == session_id, Question.candidate_answer.isnot(None))
        .order_by(Question.order_index)
        .all()
    )

    previous_qa = [
        {
            "question": q.question_text,
            "answer": q.candidate_answer,
            "score": q.score,
        }
        for q in prev_questions
    ]

    # Retrieve fresh context
    retrieved_chunks = retrieve_context(
        role=session.role,
        skills=session.extracted_skills or [],
        technologies=session.extracted_technologies or {},
        experience=session.extracted_experience or "",
    )
    context = format_context_for_prompt(retrieved_chunks)

    # Generate adaptive questions
    new_questions = generate_questions(
        role=session.role,
        skills=session.extracted_skills or [],
        technologies=session.extracted_technologies or {},
        experience_summary=session.extracted_experience or "",
        context=context,
        num_questions=3,
        previous_qa=previous_qa,
    )

    # Get current max order_index
    max_order = db.query(Question).filter(
        Question.session_id == session_id
    ).count()

    for i, qdata in enumerate(new_questions):
        q = Question(
            session_id=session.id,
            order_index=max_order + i,
            question_text=qdata["question"],
            topic=qdata.get("topic", "General"),
            difficulty=qdata.get("difficulty", "medium"),
            context_used=qdata.get("context_used", ""),
        )
        db.add(q)

    session.total_questions += len(new_questions)
    db.commit()

    return {
        "status": "success",
        "new_questions_added": len(new_questions),
        "total_questions": session.total_questions,
    }
