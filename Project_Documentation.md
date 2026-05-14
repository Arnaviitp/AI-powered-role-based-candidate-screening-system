# 🧠 AI-Powered Role-Based Candidate Screening System: Project Documentation

## 1. Executive Summary

The **AI-Powered Role-Based Candidate Screening System** is a sophisticated, end-to-end interview platform designed to automate the initial technical screening of candidates. Unlike traditional screening tools that rely on static question banks, this system leverages **Retrieval-Augmented Generation (RAG)** to dynamically generate interview questions grounded in authoritative textbook knowledge and tailored to the candidate's unique resume.

By combining modern LLMs (Google Gemini) with a robust vector search engine (ChromaDB), the platform ensures that every interview is unique, challenging, and technically sound.

---

## 2. Key Functionalities

-   **Dynamic Resume Parsing**: Automatically extracts skills, technologies, and experience summaries from PDF/TXT resumes using advanced text extraction.
-   **Intelligent RAG Pipeline**: Retrieves relevant context from a role-specific knowledge base (textbooks) to ground AI-generated questions in facts, not hallucinations.
-   **Adaptive Interview Engine**: Real-time adjustment of question difficulty based on candidate performance—pushing strong candidates and supporting those in foundational areas.
-   **Automated Evaluation**: Instant scoring and feedback for each answer, providing a consistent and unbiased grading metric.
-   **Comprehensive Analytics**: Generates a final session summary including overall scores, strengths, areas for improvement, and a hiring recommendation.

---

## 3. System Architecture

The system follows a modern decoupled architecture:

### Frontend (Next.js 15)
-   **App Router**: High-performance routing and server-side rendering where applicable.
-   **Stateful Interview UI**: A chat-like interface that manages the complex state of an ongoing interview.
-   **Design System**: A custom CSS-based design system (`globals.css`) featuring a sleek "Dark Mode" aesthetic with glassmorphism and subtle animations.

### Backend (FastAPI)
-   **Service-Oriented Design**: Business logic is separated into specialized services (RAG, Question Generator, Resume Parser).
-   **Persistent Storage**: SQLite with SQLAlchemy ORM for managing sessions, questions, and answers.
-   **Vector Search**: ChromaDB for high-speed similarity search of technical concepts.

### AI Layer
-   **LLM**: Google Gemini 1.5 Flash for question generation, answer evaluation, and summary synthesis.
-   **Embeddings**: Sentence-Transformers (`all-MiniLM-L6-v2`) for converting textbook text into searchable vectors.

---

## 4. Deep Dive: The RAG Pipeline

The "Core" of the system is the RAG (Retrieval-Augmented Generation) pipeline, which ensures technical accuracy.

### A. Knowledge Ingestion
1.  Textbooks are uploaded and processed into small, manageable chunks.
2.  **Paragraph-Aware Splitting**: Chunks are split at paragraph boundaries to maintain semantic context, with a 200-character overlap.
3.  **Vectorization**: Each chunk is transformed into a 384-dimensional vector and stored in ChromaDB.

### B. Query Expansion & Retrieval
Instead of a single search, the system performs **Multi-Query Retrieval**:
-   **Role+Skills Query**: Searches for the intersection of the role and the candidate's top skills.
-   **Tech Depth Query**: Focuses on specific technologies mentioned in the resume.
-   **Fundamental Query**: Ensures basic role-specific concepts are covered.
-   **Scenario Query**: Searches for practical applications and problem-solving contexts.

### C. Contextual Grounding
The retrieved chunks are injected into the LLM prompt, forcing the model to generate questions based *only* on the provided authoritative material.

---

## 5. The Interview Engine Logic

### Adaptive Difficulty Algorithm
The engine maintains a `previous_qa` history. When generating the next question:
1.  If the candidate scored > 8.0 on recent questions, the LLM is instructed to increase technical depth.
2.  If the candidate scored < 4.0, the system pivots to foundational concepts to find the candidate's baseline.
3.  This creates a "tapered" interview experience that finds the candidate's ceiling.

### Answer Evaluation
Answers are graded across four dimensions:
1.  **Correctness (40%)**: Accuracy against the RAG context.
2.  **Technical Depth (30%)**: Use of domain-specific terminology and conceptual understanding.
3.  **Clarity (20%)**: Structuring of the response.
4.  **Best Practices (10%)**: Mention of industry standards or edge cases.

---

## 6. Technical Stack & Tools

| Component | Technology | Rationale |
| :--- | :--- | :--- |
| **Frontend** | React / Next.js 15 | Modern, fast, and excellent SEO capabilities. |
| **Backend** | FastAPI | High performance, async-first, and native JSON support. |
| **LLM** | Google Gemini 1.5 Flash | Large context window and high speed for interactive use. |
| **Vector DB** | ChromaDB | Lightweight, open-source, and easy to deploy locally. |
| **Database** | SQLite | Serverless, portable, and sufficient for session persistence. |
| **Parser** | PyMuPDF | Robust and fast PDF text extraction. |

---

## 7. Data Schema

The system uses three primary entities:
-   **Session**: Stores candidate info (name, role, skills), resume content, and overall results.
-   **Question**: Links to a session and stores the question text, topic, difficulty, and the RAG context used.
-   **Answer** (Embedded in Question): Stores the candidate's response, AI feedback, and numerical score.

---

## 8. Frontend Design Philosophy

The UI is designed to feel **premium and professional**:
-   **Glassmorphism**: Cards use semi-transparent backgrounds with backdrop filters for a modern depth effect.
-   **Dynamic Status**: Real-time progress bars and "Q-Dots" keep the candidate informed of their progress.
-   **Typography**: Uses *Inter* for maximum legibility in technical contexts.
-   **Micro-animations**: Smooth transitions for question loading and feedback displays.

---

## 9. Future Roadmap

1.  **Voice Interaction**: Integrating Web Speech API for verbal interviews.
2.  **Code Execution**: A sandboxed environment for real-time coding challenges.
3.  **Multi-Modal RAG**: Supporting diagrams and charts from textbooks as context.
4.  **Team Collaboration**: Shared dashboards for hiring managers to review and compare candidates.

---

## 10. Security & Compliance

-   **API Key Safety**: Environment variables are used for all sensitive keys.
-   **Data Privacy**: Resumes are processed in-memory or in local storage, not stored on external clouds (except for LLM processing).
-   **Hallucination Guardrails**: Strict RAG grounding significantly reduces the risk of AI-generated misinformation.

---
*Created by the AI Engineering Team.*
