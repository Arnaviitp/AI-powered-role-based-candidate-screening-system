# 🧠 AI-Powered Role-Based Candidate Screening System

An intelligent interview platform that dynamically generates technical interview questions based on a candidate's resume, selected role, and authoritative textbook knowledge bases using **Retrieval-Augmented Generation (RAG)**.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi)
![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)
![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_Store-orange)
![Gemini](https://img.shields.io/badge/Google_Gemini-LLM-4285F4?logo=google)

---

## 📋 Table of Contents

- [Features](#-features)
- [System Architecture](#-system-architecture)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Setup Instructions](#-setup-instructions)
- [Knowledge Base Setup](#-knowledge-base-setup)
- [API Documentation](#-api-documentation)
- [Design Decisions](#-key-design-decisions)
- [Screenshots](#-screenshots)

---

## ✨ Features

- **Resume Parsing** — Extracts skills, technologies, and experience from PDF/TXT resumes
- **RAG-Powered Questions** — Questions grounded in role-specific textbook knowledge, not generic templates
- **Adaptive Difficulty** — System adjusts question difficulty based on candidate performance
- **Real-Time Evaluation** — AI-powered answer scoring with detailed feedback
- **Session Management** — Complete interview lifecycle with persistent storage
- **Comprehensive Summary** — Final report with scores, strengths, improvements, and hiring recommendation
- **5 Supported Roles** — AI/ML Engineer, Data Scientist, Backend Engineer, Frontend Engineer, Full Stack Engineer

---

## 🏗 System Architecture

```
┌──────────────────────────┐
│     Next.js Frontend     │
│  ┌────────────────────┐  │
│  │  Resume Upload     │  │
│  │  Role Selection    │  │
│  │  Interview Chat    │  │
│  │  Summary View      │  │
│  └────────┬───────────┘  │
└───────────┼──────────────┘
            │ REST API
┌───────────▼──────────────┐
│     FastAPI Backend      │
│  ┌────────────────────┐  │
│  │  Resume Parser     │──│──▶ PyMuPDF (PDF text extraction)
│  │  RAG Pipeline      │──│──▶ ChromaDB (vector similarity search)
│  │  Question Generator│──│──▶ Google Gemini (LLM)
│  │  Answer Evaluator  │  │
│  │  Session Manager   │──│──▶ SQLite (persistent storage)
│  └────────────────────┘  │
└──────────────────────────┘
```

### Data Flow

1. **Candidate uploads resume** → Backend parses PDF, extracts skills/technologies
2. **Context construction** → RAG pipeline builds queries from resume + role
3. **Knowledge retrieval** → ChromaDB returns relevant textbook chunks
4. **Question generation** → Gemini LLM generates grounded questions using retrieved context
5. **Interactive interview** → Candidate answers, system evaluates in real-time
6. **Session summary** → AI generates comprehensive assessment with scores and recommendations

---

## 🛠 Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15 (React) | UI with App Router |
| Backend | FastAPI (Python) | REST API & business logic |
| Database | SQLite + SQLAlchemy | Session & Q/A persistence |
| Vector Store | ChromaDB | Embedding storage & similarity search |
| Embeddings | Sentence-Transformers | all-MiniLM-L6-v2 for vectorization |
| LLM | Google Gemini 1.5 Flash | Question generation & answer evaluation |
| Resume Parser | PyMuPDF (fitz) | PDF text extraction |

---

## 📁 Project Structure

```
├── backend/
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Environment-based configuration
│   ├── database.py             # SQLAlchemy engine & session factory
│   ├── models.py               # ORM models (Session, Question)
│   ├── routers/
│   │   ├── sessions.py         # Session CRUD endpoints
│   │   ├── interview.py        # Interview flow endpoints
│   │   └── knowledge.py        # Knowledge base management
│   ├── services/
│   │   ├── resume_parser.py    # PDF parsing & skill extraction
│   │   ├── knowledge_ingestion.py  # Chunking, embedding, ChromaDB
│   │   ├── rag_pipeline.py     # Query construction & retrieval
│   │   └── question_generator.py   # LLM-based Q generation & evaluation
│   ├── knowledge_base/         # Role-specific textbook PDFs
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/app/
│   │   ├── layout.js           # Root layout with navbar
│   │   ├── page.js             # Landing page (upload + role select)
│   │   ├── globals.css         # Complete design system
│   │   ├── interview/[sessionId]/page.js  # Interview UI
│   │   └── summary/[sessionId]/page.js    # Results summary
│   ├── .env.local
│   └── package.json
└── README.md
```

---

## 🚀 Setup Instructions

### Prerequisites

- Python 3.10+
- Node.js 18+
- Google Gemini API key ([Get one free](https://aistudio.google.com/apikey))

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/AI-powered-role-based-candidate-screening-system.git
cd AI-powered-role-based-candidate-screening-system
```

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
# Edit .env and add your Gemini API key:
# GEMINI_API_KEY=your_actual_key_here

# Start the server
uvicorn main:app --reload --port 8000
```

### 3. Knowledge Base Setup

Place role-specific textbook PDFs in the `backend/knowledge_base/` directory. The system auto-ingests them on first use.

Recommended books (as specified in the assignment):
- **AI/ML Role**: *Machine Learning — Tom Mitchell*, *The Hundred-Page ML Book — Andriy Burkov*
- **Data Science**: *Introduction to ML with Python*, *Master ML Algorithms — Jason Brownlee*

### 4. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 5. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 📚 Knowledge Base Setup

The RAG pipeline requires role-specific documents. Place PDF or TXT files in:

```
backend/knowledge_base/
```

The system will automatically:
1. Extract text from documents
2. Chunk text with paragraph-aware splitting (1000 chars, 200 overlap)
3. Generate embeddings using sentence-transformers
4. Store vectors in ChromaDB for fast retrieval

You can also upload documents via the API:
```bash
curl -X POST http://localhost:8000/api/knowledge/upload \
  -F "file=@textbook.pdf" \
  -F "role=AI/ML Engineer"
```

---

## 📡 API Documentation

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/sessions` | Create session (upload resume + select role) |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Get session details |
| DELETE | `/api/sessions/{id}` | Delete a session |

### Interview
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/interview/{id}/current-question` | Get current question |
| POST | `/api/interview/{id}/answer/{qid}` | Submit answer |
| GET | `/api/interview/{id}/summary` | Get session summary |
| POST | `/api/interview/{id}/generate-more-questions` | Generate adaptive questions |

### Knowledge Base
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/knowledge/upload` | Upload knowledge document |
| POST | `/api/knowledge/ingest/{role}` | Trigger ingestion |
| GET | `/api/knowledge/status` | Check KB status |

---

## 🎯 Key Design Decisions

### 1. Chunking Strategy
**Paragraph-aware chunking** with 200-char overlap preserves context boundaries better than naive fixed-size splitting. Long paragraphs are further split on sentence boundaries.

### 2. Query Construction
Queries are **dynamically built from resume data** — not static templates. The system creates 5-6 targeted queries combining skills, technologies, and experience context to maximize retrieval relevance.

### 3. Question Grounding
Every generated question is **grounded in retrieved textbook content**, not internet knowledge. The LLM prompt includes the exact context chunks, ensuring questions are authoritative and relevant.

### 4. Adaptive Difficulty
The system passes previous Q&A history to the LLM, allowing it to **adjust difficulty based on performance** — harder questions for strong candidates, foundational revisits for weak areas.

### 5. Separation of Concerns
- **Services** handle business logic (parsing, RAG, generation)
- **Routers** handle HTTP concerns (validation, serialization)
- **Models** define data structure
- **Config** centralizes environment management

### 6. Vector Database Choice
ChromaDB was chosen for its **zero-configuration setup** — no external services needed. It supports persistent storage and built-in embedding functions.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.