"""Resume parsing service – extracts structured data from PDF/text resumes."""

import re
import fitz  # PyMuPDF
from pathlib import Path


def extract_text_from_pdf(file_path: str) -> str:
    """Extract raw text from a PDF file using PyMuPDF."""
    doc = fitz.open(file_path)
    text_parts = []
    for page in doc:
        text_parts.append(page.get_text())
    doc.close()
    return "\n".join(text_parts)


def extract_text_from_txt(file_path: str) -> str:
    """Read raw text from a plain text file."""
    return Path(file_path).read_text(encoding="utf-8")


def extract_text(file_path: str) -> str:
    """Auto-detect format and extract text."""
    ext = Path(file_path).suffix.lower()
    if ext == ".pdf":
        return extract_text_from_pdf(file_path)
    elif ext in (".txt", ".text", ".md"):
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


# ── Skill / technology extraction heuristics ──────────────────────────

TECH_KEYWORDS = {
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
    "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    # Frameworks
    "react", "angular", "vue", "next.js", "nextjs", "django", "flask", "fastapi",
    "spring", "express", "node.js", "nodejs", "rails", "laravel",
    # ML / AI
    "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "opencv",
    "transformers", "hugging face", "huggingface", "langchain", "llm",
    "machine learning", "deep learning", "nlp", "natural language processing",
    "computer vision", "reinforcement learning", "neural network", "cnn", "rnn",
    "lstm", "gpt", "bert", "rag", "retrieval augmented generation",
    # Data
    "pandas", "numpy", "spark", "hadoop", "kafka", "airflow", "dbt",
    "tableau", "power bi", "matplotlib", "seaborn", "plotly",
    # Cloud & DevOps
    "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
    "github actions", "jenkins", "linux",
    # Databases
    "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "chromadb",
    "pinecone", "weaviate", "sqlite", "dynamodb", "cassandra",
    # Others
    "git", "rest", "graphql", "grpc", "microservices", "api",
}

SKILL_CATEGORIES = {
    "programming_languages": {
        "python", "java", "javascript", "typescript", "c++", "c#", "go", "rust",
        "ruby", "php", "swift", "kotlin", "scala", "r", "matlab", "sql", "bash",
    },
    "ml_ai": {
        "tensorflow", "pytorch", "keras", "scikit-learn", "sklearn", "opencv",
        "transformers", "hugging face", "huggingface", "langchain", "llm",
        "machine learning", "deep learning", "nlp", "natural language processing",
        "computer vision", "reinforcement learning", "neural network", "cnn", "rnn",
        "lstm", "gpt", "bert", "rag",
    },
    "web_frameworks": {
        "react", "angular", "vue", "next.js", "nextjs", "django", "flask", "fastapi",
        "spring", "express", "node.js", "nodejs", "rails", "laravel",
    },
    "databases": {
        "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "chromadb",
        "pinecone", "weaviate", "sqlite", "dynamodb", "cassandra",
    },
    "cloud_devops": {
        "aws", "gcp", "azure", "docker", "kubernetes", "terraform", "ci/cd",
        "github actions", "jenkins", "linux",
    },
}


def extract_skills(text: str) -> list[str]:
    """Extract technical skills mentioned in the resume text."""
    text_lower = text.lower()
    found = []
    for kw in TECH_KEYWORDS:
        # Use word boundary matching for short keywords
        if len(kw) <= 3:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, text_lower):
                found.append(kw)
        else:
            if kw in text_lower:
                found.append(kw)
    return sorted(set(found))


def extract_technologies(text: str) -> dict[str, list[str]]:
    """Categorise extracted skills into technology groups."""
    text_lower = text.lower()
    result: dict[str, list[str]] = {}
    for category, keywords in SKILL_CATEGORIES.items():
        matches = []
        for kw in keywords:
            if len(kw) <= 3:
                if re.search(rf"\b{re.escape(kw)}\b", text_lower):
                    matches.append(kw)
            else:
                if kw in text_lower:
                    matches.append(kw)
        if matches:
            result[category] = sorted(set(matches))
    return result


def extract_experience_summary(text: str) -> str:
    """Attempt to extract an experience / background summary from the resume."""
    lines = text.split("\n")
    experience_section = []
    capture = False
    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()
        # Detect section headers
        if any(h in lower for h in ["experience", "work history", "employment", "projects"]):
            capture = True
            continue
        if capture:
            # Stop at next major section
            if any(h in lower for h in ["education", "skills", "certifications",
                                         "awards", "publications", "references"]):
                break
            if stripped:
                experience_section.append(stripped)

    if experience_section:
        return "\n".join(experience_section[:30])  # cap length

    # Fallback: return the first 500 chars
    return text[:500]


def parse_resume(file_path: str) -> dict:
    """
    Full resume parsing pipeline.
    Returns a dict with raw text, skills, technologies, and experience summary.
    """
    text = extract_text(file_path)
    skills = extract_skills(text)
    technologies = extract_technologies(text)
    experience = extract_experience_summary(text)

    return {
        "raw_text": text,
        "skills": skills,
        "technologies": technologies,
        "experience_summary": experience,
    }
