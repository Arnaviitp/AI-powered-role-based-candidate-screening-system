"""
Question generation service using Google Gemini LLM (new google-genai SDK).

Generates interview questions grounded in:
- Retrieved RAG context (from role-specific knowledge base)
- Candidate's resume (skills, technologies, experience)
- Previous Q&A history for adaptive difficulty
"""

import json
import os
import re
import time
import urllib.error
import urllib.request
from google import genai
from google.genai import types
from config import (
    AI_PROVIDER_ORDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_MS,
    GROQ_API_KEY,
    GROQ_MODEL,
)

# Configure Gemini client
_gemini_client = None

MAX_RETRIES = 4
BASE_DELAY = 15  # seconds — free tier asks for ~48s, so we space retries out


def _get_client():
    return _get_gemini_client()


def _get_gemini_client():
    global _gemini_client
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")
    if _gemini_client is None:
        # The google-genai SDK gives GOOGLE_API_KEY precedence if it exists.
        # This app is configured with GEMINI_API_KEY, so remove stale process
        # values before creating the client.
        os.environ.pop("GOOGLE_API_KEY", None)
        _gemini_client = genai.Client(
            api_key=GEMINI_API_KEY,
            http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_MS),
        )
    return _gemini_client


def _generate_with_gemini(prompt: str, *, max_retries: int = MAX_RETRIES) -> str:
    """Send a prompt to Gemini with retry logic for rate-limit (429) errors."""
    client = _get_gemini_client()
    last_err = None

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            last_err = e
            err_str = str(e)
            # Retry only on rate-limit / quota errors
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                if attempt == max_retries - 1:
                    break
                # Extract suggested retry delay if available
                delay = BASE_DELAY * (2 ** attempt)
                # Check if the error message contains a specific retry delay
                match = re.search(r"retry in ([\d.]+)s", err_str, re.IGNORECASE)
                if match:
                    delay = max(delay, float(match.group(1)) + 2)
                print(f"[Gemini] Rate limited (attempt {attempt+1}/{max_retries}). "
                      f"Retrying in {delay:.0f}s...")
                time.sleep(delay)
            else:
                # Non-retryable error, raise immediately
                raise

    # All retries exhausted
    raise last_err


def _generate_with_groq(prompt: str) -> str:
    """Send a prompt to Groq as a secondary cloud LLM provider."""
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")

    payload = {
        "model": GROQ_MODEL,
        "temperature": 0.2,
        "messages": [
            {
                "role": "system",
                "content": "You are a precise technical interviewer. Return only valid JSON.",
            },
            {"role": "user", "content": prompt},
        ],
    }
    request = urllib.request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=GEMINI_TIMEOUT_MS / 1000) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"Groq HTTP {e.code}: {detail}") from e

    return data["choices"][0]["message"]["content"].strip()


def _generate(prompt: str, *, max_retries: int = MAX_RETRIES) -> str:
    """Generate text with configured cloud providers before local fallback."""
    errors = []
    providers = AI_PROVIDER_ORDER or ["gemini", "groq"]

    for provider in providers:
        try:
            if provider == "gemini":
                return _generate_with_gemini(prompt, max_retries=max_retries)
            if provider == "groq":
                return _generate_with_groq(prompt)
            errors.append(f"{provider}: unknown provider")
        except Exception as e:
            errors.append(f"{provider}: {e}")

    raise RuntimeError("All AI providers failed. " + " | ".join(errors))


def _summarize_provider_error(error: Exception) -> str:
    message = str(error)
    if "groq: Groq HTTP 403" in message or "Groq HTTP 403" in message:
        return "Groq rejected the configured API key or account access."
    if "RESOURCE_EXHAUSTED" in message or "quota" in message.lower():
        return "AI quota is exhausted for the configured Gemini project."
    if "401" in message or "API key" in message:
        return "An AI API key is missing or invalid."
    if "WinError 10013" in message or "urlopen error" in message:
        return "Network access to the AI provider is blocked."
    return "All configured AI providers failed."


def check_ai_connection() -> dict:
    """Return a small diagnostic payload for the configured Gemini client."""
    if not GEMINI_API_KEY:
        return {
            "available": False,
            "model": GEMINI_MODEL,
            "reason": "GEMINI_API_KEY is not configured",
        }

    try:
        raw = _generate(
            'Return exactly this JSON and nothing else: {"status":"ok","score":1}',
            max_retries=1,
        )
        parsed = _extract_json(raw)
        return {
            "available": parsed.get("status") == "ok",
            "provider_order": AI_PROVIDER_ORDER,
            "model": f"gemini={GEMINI_MODEL}, groq={GROQ_MODEL}",
            "reason": None,
        }
    except Exception as e:
        return {
            "available": False,
            "provider_order": AI_PROVIDER_ORDER,
            "model": f"gemini={GEMINI_MODEL}, groq={GROQ_MODEL}",
            "reason": _summarize_provider_error(e),
        }


def _extract_json(raw: str):
    """Robustly extract JSON from LLM response, handling markdown fences and extra text."""
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw)
    cleaned = re.sub(r"```", "", cleaned)
    cleaned = cleaned.strip()

    # Try to find the first '{' and last '}' or first '[' and last ']'
    start_brace = cleaned.find('{')
    end_brace = cleaned.rfind('}')
    start_bracket = cleaned.find('[')
    end_bracket = cleaned.rfind(']')

    # If we found a potential object
    if start_brace != -1 and end_brace != -1 and (start_bracket == -1 or start_brace < start_bracket):
        json_str = cleaned[start_brace:end_brace+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # If we found a potential array
    if start_bracket != -1 and end_bracket != -1:
        json_str = cleaned[start_bracket:end_bracket+1]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass

    # Fallback to direct parse if nothing else worked
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        raise ValueError(f"Could not extract valid JSON from response: {raw[:200]}...")


def _format_technologies(technologies) -> str:
    """Safely format technologies regardless of whether it's a dict, list, or string."""
    if not technologies:
        return "Not specified"
    if isinstance(technologies, dict):
        return json.dumps(technologies)
    if isinstance(technologies, list):
        return ", ".join(str(t) for t in technologies)
    return str(technologies)


def generate_questions(
    role: str,
    skills: list[str],
    technologies,
    experience_summary: str,
    context: str,
    num_questions: int = 5,
    previous_qa: list[dict] | None = None,
) -> list[dict]:
    """
    Generate interview questions using the Gemini LLM.

    Returns a list of dicts:
        [{"question": str, "topic": str, "difficulty": str, "context_used": str}]
    """
    previous_context = ""
    if previous_qa:
        qa_lines = []
        for qa in previous_qa[-3:]:  # Last 3 Q&A for context
            qa_lines.append(f"Q: {qa['question']}")
            if qa.get("answer"):
                qa_lines.append(f"A: {qa['answer'][:200]}")
                if qa.get("score") is not None:
                    qa_lines.append(f"Score: {qa['score']}/10")
        previous_context = "\n".join(qa_lines)

    tech_str = _format_technologies(technologies)

    prompt = f"""You are an expert technical interviewer conducting a structured interview for the role of **{role}**.

## Candidate Profile
- **Skills**: {', '.join(skills) if skills else 'Not specified'}
- **Technologies**: {tech_str}
- **Experience Summary**: {experience_summary[:500] if experience_summary else 'Not specified'}

## Knowledge Base Context (from authoritative textbooks)
{context}

{f"## Previous Questions & Answers (adapt difficulty based on performance):{chr(10)}{previous_context}" if previous_context else ""}

## Instructions
Generate exactly {num_questions} interview questions. Follow these rules:
1. Questions MUST be grounded in the knowledge base context provided above
2. Questions should be tailored to the candidate's specific skills and experience
3. Include a mix of difficulties: some foundational, some intermediate, some advanced
4. Questions should test conceptual understanding, not just recall
5. Include at least one applied/scenario-based question
6. If previous Q&A is provided, adapt: ask harder questions if candidate scored well, or revisit weak areas
7. Do NOT generate generic questions – each must relate to specific content from the context

## Output Format
Return a JSON array with exactly {num_questions} objects. Each object must have:
- "question": The interview question (string)
- "topic": The topic area being tested (string)
- "difficulty": One of "easy", "medium", or "hard" (string)
- "context_used": A brief snippet of the context that inspired this question (string, max 100 chars)

Return ONLY the JSON array, no other text."""

    try:
        raw = _generate(prompt)
        questions = _extract_json(raw)

        # Validate structure
        validated = []
        for q in questions:
            if isinstance(q, dict) and "question" in q:
                validated.append({
                    "question": q["question"],
                    "topic": q.get("topic", "General"),
                    "difficulty": q.get("difficulty", "medium"),
                    "context_used": q.get("context_used", "")[:200],
                })
        return validated[:num_questions]

    except Exception as e:
        # Fallback: return basic questions if LLM fails
        print(f"[QuestionGenerator] Falling back to local questions: {_summarize_provider_error(e)}")
        return _fallback_questions(role, skills, num_questions)


def _fallback_questions(role: str, skills: list[str], n: int) -> list[dict]:
    """Generate basic fallback questions if the LLM is unavailable."""
    questions = []
    base_topics = skills[:n] if skills else ["general knowledge"]
    for i, topic in enumerate(base_topics):
        questions.append({
            "question": f"Can you explain your experience with {topic} and how you've applied it in the context of {role}?",
            "topic": topic,
            "difficulty": "medium",
            "context_used": "Fallback – no RAG context",
        })
    # Pad if needed
    while len(questions) < n:
        questions.append({
            "question": f"What do you consider the most important skill for a {role} and why?",
            "topic": "General",
            "difficulty": "easy",
            "context_used": "Fallback – no RAG context",
        })
    return questions[:n]


def evaluate_answer(
    question: str,
    answer: str,
    role: str,
    context: str = "",
) -> dict:
    """
    Evaluate a candidate's answer using the LLM.
    Returns: {"score": float, "feedback": str}
    """
    prompt = f"""You are an expert technical interviewer evaluating a candidate's answer for the role of **{role}**.

## Question
{question}

## Candidate's Answer
{answer}

## Reference Context (from knowledge base)
{context if context else "No specific context available."}

## Evaluation Criteria
1. **Correctness & Accuracy** (0-4): Is the answer factually correct and aligned with the provided context? Deduct points for even minor inaccuracies.
2. **Technical Depth & Insight** (0-3): Does the candidate demonstrate a deep understanding of underlying principles, or just repeat keywords?
3. **Clarity & Articulation** (0-2): Is the response well-structured and easy to understand?
4. **Best Practices & Edge Cases** (0-1): Does the candidate mention relevant industry standards or potential pitfalls?

## Scoring Instructions
- **Highly Discriminative**: Use the full 0.0 to 10.0 scale. Do NOT default to middle scores like 7 or 8.
- **Strict Grading**: If an answer is basic or generic, it should receive a 3 or 4. Only truly outstanding, comprehensive, and insightful answers should get a 9 or 10.
- **Granular Scores**: Provide scores with at least one decimal place (e.g., 6.4, 7.8) to ensure differentiation between candidates.
- **Feedback**: Be critical yet constructive. Highlight exactly what was missing for a perfect score.

## Output Format
Return a JSON object with exactly these keys:
- "score": A float from 0.0 to 10.0 (one decimal place)
- "feedback": A detailed 3-4 sentence evaluation.

IMPORTANT: Return ONLY the raw JSON object. Do NOT wrap it in markdown code blocks."""

    try:
        raw = _generate(prompt)
        print(f"[AnswerEvaluator] Raw LLM response: {raw[:300]}")

        result = _extract_json(raw)
        score = min(10.0, max(0.0, float(result.get("score", 5.0))))
        feedback = result.get("feedback", "Answer evaluated.")
        print(f"[AnswerEvaluator] Parsed score={score}, feedback={feedback[:80]}")
        return {
            "score": round(score, 1),
            "feedback": feedback,
        }
    except Exception as e:
        reason = _summarize_provider_error(e)
        print(f"[AnswerEvaluator] Falling back to local evaluation: {reason}")
        return {
            "score": 5.0,
            "feedback": f"{reason} Answer recorded without AI scoring.",
            "fallback": True,
        }


def generate_session_summary(
    role: str,
    skills: list[str],
    questions_and_answers: list[dict],
) -> dict:
    """
    Generate a comprehensive session summary using the LLM.
    Returns: {"summary": str, "overall_score": float, "strengths": list, "improvements": list}
    """
    qa_text = ""
    for qa in questions_and_answers:
        qa_text += f"\nQ{qa['order']}: [{qa['difficulty']}] {qa['question']}\n"
        qa_text += f"A: {qa['answer'] or 'Not answered'}\n"
        qa_text += f"Score: {qa['score']}/10 – {qa['feedback']}\n"

    prompt = f"""You are a senior technical interviewer providing a final assessment for a candidate applying for **{role}**.

## Candidate Skills
{', '.join(skills) if skills else 'Not specified'}

## Interview Transcript
{qa_text}

## Instructions
Provide a comprehensive evaluation. Return a JSON object with:
- "overall_score": Average score out of 10 (float)
- "summary": A 3-5 sentence overall assessment (string)
- "strengths": Array of 2-4 specific strengths observed (array of strings)
- "improvements": Array of 2-4 areas for improvement (array of strings)  
- "recommendation": One of "Strong Hire", "Hire", "Maybe", "No Hire" (string)
- "topic_scores": Object mapping topic names to scores (object)

Return ONLY the JSON object, no other text."""

    try:
        raw = _generate(prompt)
        result = _extract_json(raw)

        # Validate and sanitize the parsed result
        overall_score = min(10.0, max(0.0, float(result.get("overall_score", 5.0))))
        return {
            "overall_score": round(overall_score, 1),
            "summary": result.get("summary", "Interview session completed."),
            "strengths": result.get("strengths", ["Completed all questions"]),
            "improvements": result.get("improvements", ["Review needed"]),
            "recommendation": result.get("recommendation", "Maybe"),
            "topic_scores": result.get("topic_scores", {}),
        }
    except Exception as e:
        print(f"[SummaryGenerator] Falling back to local summary: {_summarize_provider_error(e)}")
        scores = [qa.get("score", 5) for qa in questions_and_answers if qa.get("score")]
        avg = sum(scores) / len(scores) if scores else 5.0
        return {
            "overall_score": round(avg, 1),
            "summary": "Interview session completed. Please review individual responses.",
            "strengths": ["Completed all questions"],
            "improvements": ["Review needed"],
            "recommendation": "Maybe",
            "topic_scores": {},
        }
