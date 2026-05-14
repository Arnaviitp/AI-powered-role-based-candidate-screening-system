"""
RAG pipeline – orchestrates context construction, knowledge retrieval,
and prompt generation for the interview question workflow.
"""

from config import TOP_K_RESULTS
from services.knowledge_ingestion import query_knowledge_base


def build_retrieval_queries(role: str, skills: list[str],
                             technologies: dict, experience: str) -> list[str]:
    """
    Dynamically construct queries for the vector store based on
    resume content and the selected role.
    """
    queries = []

    # Query 1: Role + top skills
    top_skills = skills[:5] if skills else ["general"]
    queries.append(f"{role} concepts related to {', '.join(top_skills)}")

    # Query 2: Technology-specific depth questions
    for category, techs in technologies.items():
        if techs:
            queries.append(f"Advanced concepts in {', '.join(techs[:3])} for {role}")

    # Query 3: From experience context
    if experience:
        exp_snippet = experience[:200].replace("\n", " ")
        queries.append(f"Technical topics relevant to: {exp_snippet}")

    # Query 4: Role fundamentals
    queries.append(f"Fundamental concepts every {role} should know")

    # Query 5: Applied / practical
    queries.append(f"Practical applications and problem-solving in {role}")

    return queries[:6]  # Cap at 6 queries


def retrieve_context(role: str, skills: list[str],
                      technologies: dict, experience: str) -> list[dict]:
    """
    Full RAG retrieval step:
    1. Build queries from resume data
    2. Query the vector store
    3. De-duplicate and rank results
    """
    queries = build_retrieval_queries(role, skills, technologies, experience)
    all_results = []
    seen_contents = set()

    for query in queries:
        results = query_knowledge_base(role, [query], n_results=TOP_K_RESULTS)
        for r in results:
            # De-duplicate by content hash
            content_key = r["content"][:100]
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                all_results.append(r)

    # Sort by relevance
    all_results.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return all_results[:TOP_K_RESULTS * 2]  # Return top results


def format_context_for_prompt(retrieved_chunks: list[dict]) -> str:
    """Format retrieved chunks into a prompt-ready context block."""
    if not retrieved_chunks:
        return "No specific knowledge base context available."

    context_parts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        source = chunk.get("source", "unknown")
        content = chunk["content"].strip()
        context_parts.append(
            f"[Source {i}: {source}]\n{content}"
        )

    return "\n\n---\n\n".join(context_parts)
