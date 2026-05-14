"""SQLAlchemy ORM models for the screening system."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Session(Base):
    """Represents a single interview session for one candidate."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    candidate_name = Column(String(255), nullable=True)
    role = Column(String(100), nullable=False)
    resume_text = Column(Text, nullable=False)
    resume_filename = Column(String(255), nullable=True)
    extracted_skills = Column(JSON, nullable=True)  # list of skills
    extracted_technologies = Column(JSON, nullable=True)
    extracted_experience = Column(Text, nullable=True)
    status = Column(String(20), default="active")  # active | completed
    processing_status = Column(String(50), default="pending") # pending | parsing | indexing | retrieving | generating | ready | failed
    processing_progress = Column(Integer, default=0) # 0-100
    current_question_index = Column(Integer, default=0)
    total_questions = Column(Integer, default=10)
    overall_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)

    questions = relationship("Question", back_populates="session", cascade="all, delete-orphan",
                             order_by="Question.order_index")

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_name": self.candidate_name,
            "role": self.role,
            "resume_filename": self.resume_filename,
            "extracted_skills": self.extracted_skills,
            "extracted_technologies": self.extracted_technologies,
            "status": self.status,
            "processing_status": self.processing_status,
            "processing_progress": self.processing_progress,
            "current_question_index": self.current_question_index,
            "total_questions": self.total_questions,
            "overall_score": self.overall_score,
            "summary": self.summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class Question(Base):
    """A single interview question with its answer and evaluation."""
    __tablename__ = "questions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    session_id = Column(String(36), ForeignKey("sessions.id"), nullable=False)
    order_index = Column(Integer, nullable=False)
    question_text = Column(Text, nullable=False)
    context_used = Column(Text, nullable=True)  # RAG context that generated this question
    topic = Column(String(255), nullable=True)
    difficulty = Column(String(20), nullable=True)  # easy | medium | hard
    candidate_answer = Column(Text, nullable=True)
    score = Column(Float, nullable=True)  # 0.0 – 10.0
    feedback = Column(Text, nullable=True)
    answered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    session = relationship("Session", back_populates="questions")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "order_index": self.order_index,
            "question_text": self.question_text,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "candidate_answer": self.candidate_answer,
            "score": self.score,
            "feedback": self.feedback,
            "answered_at": self.answered_at.isoformat() if self.answered_at else None,
        }
