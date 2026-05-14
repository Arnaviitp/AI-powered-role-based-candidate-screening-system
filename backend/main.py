"""
AI-Powered Role-Based Candidate Screening System — FastAPI Backend

Main application entry point.
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from config import SUPPORTED_ROLES
from routers import sessions, interview, knowledge
from services.question_generator import check_ai_connection

# ── Logging ──────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


# ── Lifespan ─────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize resources on startup, clean up on shutdown."""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized. Server is ready.")
    yield
    logger.info("Server shutting down.")


# ── Application ──────────────────────────────────────────────────────
app = FastAPI(
    title="AI Candidate Screening System",
    description="An AI-powered role-based candidate screening system with RAG-driven interview questions.",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────
app.include_router(sessions.router)
app.include_router(interview.router)
app.include_router(knowledge.router)


# ── Health & Info ────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "AI Candidate Screening System",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/api/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/roles")
async def get_roles():
    return {"roles": SUPPORTED_ROLES}


@app.get("/api/ai/health")
async def ai_health():
    return check_ai_connection()
