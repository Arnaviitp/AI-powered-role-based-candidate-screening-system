import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True)

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", str(BASE_DIR / "uploads")))
KNOWLEDGE_BASE_DIR = Path(os.getenv("KNOWLEDGE_BASE_DIR", str(BASE_DIR / "knowledge_base")))
CHROMA_PERSIST_DIR = str(os.getenv("CHROMA_PERSIST_DIR", str(BASE_DIR / "chroma_db")))

# ── Database ───────────────────────────────────────────────────────────
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{BASE_DIR / 'screening.db'}")

# ── AI / LLM ──────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
GEMINI_TIMEOUT_MS = int(os.getenv("GEMINI_TIMEOUT_MS", "20000"))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")
AI_PROVIDER_ORDER = [
    provider.strip().lower()
    for provider in os.getenv("AI_PROVIDER_ORDER", "gemini,groq").split(",")
    if provider.strip()
]

# ── RAG Settings ──────────────────────────────────────────────────────
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
TOP_K_RESULTS = int(os.getenv("TOP_K_RESULTS", "5"))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# ── Interview Settings ────────────────────────────────────────────────
QUESTIONS_PER_SESSION = int(os.getenv("QUESTIONS_PER_SESSION", "10"))

# ── Supported Roles ──────────────────────────────────────────────────
SUPPORTED_ROLES = [
    "AI/ML Engineer",
    "Data Scientist",
    "Backend Engineer",
    "Frontend Engineer",
    "Full Stack Engineer",
]

# Ensure directories exist
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
