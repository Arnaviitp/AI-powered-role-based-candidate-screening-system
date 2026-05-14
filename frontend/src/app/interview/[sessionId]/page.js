"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function InterviewPage() {
  const { sessionId } = useParams();
  const router = useRouter();
  const textareaRef = useRef(null);
  const [session, setSession] = useState(null);
  const [currentQ, setCurrentQ] = useState(null);
  const [answer, setAnswer] = useState("");
  const [feedback, setFeedback] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [history, setHistory] = useState([]);

  const loadCurrentQuestion = useCallback(async () => {
    const res = await fetch(`${API}/api/interview/${sessionId}/current-question`);
    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      throw new Error(data.detail || "Failed to load the current question.");
    }

    if (data.status === "completed" || data.status === "all_answered") {
      router.push(`/summary/${sessionId}`);
      return data;
    }

    setCurrentQ(data);
    setFeedback(null);
    setAnswer("");
    return data;
  }, [sessionId, router]);

  const loadSession = useCallback(async () => {
    try {
      setError("");
      const res = await fetch(`${API}/api/sessions/${sessionId}`);
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Session not found.");
      }

      setSession(data);
      setHistory(data.questions || []);
      await loadCurrentQuestion();
    } catch (e) {
      setError(e.message || "Failed to load the interview.");
    } finally {
      setLoading(false);
    }
  }, [sessionId, loadCurrentQuestion]);

  useEffect(() => {
    loadSession();
  }, [loadSession]);

  const refreshSession = async () => {
    const res = await fetch(`${API}/api/sessions/${sessionId}`);
    if (!res.ok) return;
    const data = await res.json();
    setSession(data);
    setHistory(data.questions || []);
  };

  const handleSubmit = async () => {
    if (!answer.trim() || !currentQ?.question_id) return;

    setSubmitting(true);
    setError("");

    try {
      const res = await fetch(
        `${API}/api/interview/${sessionId}/answer/${currentQ.question_id}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ answer: answer.trim() }),
        },
      );
      const data = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(data.detail || "Failed to submit the answer.");
      }

      setFeedback(data);
      await refreshSession();

      if (data.is_complete) {
        setTimeout(() => router.push(`/summary/${sessionId}`), 1800);
      }
    } catch (e) {
      setError(e.message || "Unable to submit your answer.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => {
    if (feedback?.is_complete) {
      router.push(`/summary/${sessionId}`);
    } else {
      loadCurrentQuestion().catch((e) =>
        setError(e.message || "Failed to load the next question."),
      );
    }
  };

  const getScoreColor = (score) => {
    if (score >= 8) return "var(--success)";
    if (score >= 5) return "var(--warning)";
    return "var(--danger)";
  };

  const answeredCount = history.filter((q) => q.candidate_answer).length;
  const totalQuestions = session?.total_questions || currentQ?.total_questions || 1;
  const progress = Math.min(100, Math.round((answeredCount / totalQuestions) * 100));

  if (loading) {
    return (
      <main className="container">
        <div className="loading-screen">
          <div className="spinner spinner-lg"></div>
          <h2>Loading interview</h2>
          <p>Setting up your session.</p>
        </div>
      </main>
    );
  }

  if (error && !session) {
    return (
      <main className="container center-state">
        <h2>Something went wrong</h2>
        <p>{error}</p>
        <a href="/" className="btn btn-primary">
          Back to home
        </a>
      </main>
    );
  }

  return (
    <main className="container">
      <div className="interview-layout">
        <aside className="sidebar">
          <section className="card">
            <h3>Progress</h3>
            <div className="progress">
              <div className="progress-bar" style={{ width: `${progress}%` }}></div>
            </div>
            <p className="progress-copy">
              {answeredCount} of {totalQuestions} answered
            </p>

            <h3>Questions</h3>
            <ul className="q-list">
              {history.map((question, index) => (
                <li
                  key={question.id}
                  className={
                    currentQ?.question_id === question.id
                      ? "active"
                      : question.candidate_answer
                        ? "answered"
                        : ""
                  }
                >
                  <span className="q-dot"></span>
                  <span className="q-title">Q{index + 1}: {question.topic || "Question"}</span>
                  {question.score !== null && question.score !== undefined && (
                    <span className="badge badge-accent q-score">{question.score}/10</span>
                  )}
                </li>
              ))}
            </ul>
          </section>

          {session && (
            <section className="card candidate-card">
              <h3>Candidate</h3>
              <p className="candidate-name">{session.candidate_name}</p>
              <p className="candidate-role">{session.role}</p>
              {session.extracted_skills?.length > 0 && (
                <div className="skill-list">
                  {session.extracted_skills.slice(0, 8).map((skill) => (
                    <span key={skill} className="badge badge-accent">
                      {skill}
                    </span>
                  ))}
                </div>
              )}
            </section>
          )}
        </aside>

        <section className="chat-area">
          {error && <div className="error-alert">{error}</div>}

          {currentQ && currentQ.status === "active" && (
            <article className="question-card card animate-slide" key={currentQ.question_id}>
              <div className="question-header">
                <span className="question-number">
                  Question {currentQ.question_number} of {currentQ.total_questions}
                </span>
                <div className="badge-row">
                  <span className="badge badge-accent">{currentQ.topic}</span>
                  <span className={`badge badge-${currentQ.difficulty}`}>
                    {currentQ.difficulty}
                  </span>
                </div>
              </div>

              <div className="question-text">{currentQ.question_text}</div>

              <div className="answer-area">
                <label className="label" htmlFor="answer">
                  Your answer
                </label>
                <textarea
                  ref={textareaRef}
                  id="answer"
                  className="textarea"
                  placeholder="Type a detailed, specific answer."
                  value={answer}
                  onChange={(e) => setAnswer(e.target.value)}
                  rows={6}
                  disabled={submitting || !!feedback}
                />
                <div className="answer-actions">
                  {!feedback ? (
                    <button
                      className="btn btn-primary"
                      onClick={handleSubmit}
                      disabled={!answer.trim() || submitting}
                      type="button"
                    >
                      {submitting ? (
                        <>
                          <span className="spinner"></span>
                          Evaluating
                        </>
                      ) : (
                        "Submit answer"
                      )}
                    </button>
                  ) : (
                    <button className="btn btn-primary" onClick={handleNext} type="button">
                      {feedback.is_complete ? "View summary" : "Next question"}
                    </button>
                  )}
                </div>
              </div>
            </article>
          )}

          {feedback && (
            <article className="feedback-card card animate-fade">
              <div className="feedback-score">
                <span className="score-num" style={{ color: getScoreColor(feedback.score) }}>
                  {feedback.score}
                </span>
                <span>/ 10</span>
              </div>
              {feedback.fallback && (
                <div className="fallback-alert">AI provider unavailable</div>
              )}
              <p className="feedback-text">{feedback.feedback}</p>
              {feedback.is_complete && (
                <p className="completion-copy">Interview complete. Redirecting to summary.</p>
              )}
              {!feedback.is_complete && feedback.questions_remaining > 0 && (
                <p className="remaining-copy">
                  {feedback.questions_remaining} question
                  {feedback.questions_remaining === 1 ? "" : "s"} remaining
                </p>
              )}
            </article>
          )}
        </section>
      </div>
    </main>
  );
}
