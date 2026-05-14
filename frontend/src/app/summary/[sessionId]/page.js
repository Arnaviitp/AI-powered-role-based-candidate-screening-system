"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function SummaryPage() {
  const { sessionId } = useParams();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API}/api/interview/${sessionId}/summary`);
      const payload = await res.json().catch(() => ({}));

      if (!res.ok) {
        throw new Error(payload.detail || "Failed to load the summary.");
      }

      setData(payload);
    } catch (e) {
      setError(e.message || "Could not generate the summary.");
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const getScoreColor = (score) =>
    score >= 8 ? "var(--success)" : score >= 5 ? "var(--warning)" : "var(--danger)";
  const getRecClass = (recommendation) =>
    (recommendation || "").toLowerCase().replace(/\s+/g, "-");

  if (loading) {
    return (
      <main className="container">
        <div className="loading-screen">
          <div className="spinner spinner-lg"></div>
          <h2>Generating summary</h2>
          <p>Analyzing responses and preparing the assessment.</p>
        </div>
      </main>
    );
  }

  if (error || !data) {
    return (
      <main className="container center-state">
        <h2>{error || "Session not found"}</h2>
        <p>Could not generate the interview summary.</p>
        <a href="/" className="btn btn-primary">
          Back to home
        </a>
      </main>
    );
  }

  const questions = data.questions || [];
  const answered = questions.filter((question) => question.answer);
  const avgScore = Number(data.overall_score || 0);

  return (
    <main className="container animate-fade">
      <header className="summary-header">
        <h1>Interview summary</h1>
        <p>
          {data.candidate_name} | {data.role}
        </p>
        {data.recommendation && (
          <div className={`recommendation-badge ${getRecClass(data.recommendation)}`}>
            {data.recommendation}
          </div>
        )}
      </header>

      <section className="summary-stats">
        <div className="card stat-card accent">
          <div className="stat-value">{avgScore.toFixed(1)}</div>
          <div className="stat-label">Overall score</div>
        </div>
        <div className="card stat-card success">
          <div className="stat-value">{answered.length}</div>
          <div className="stat-label">Answered</div>
        </div>
        <div className="card stat-card warning">
          <div className="stat-value">
            {answered.filter((question) => question.score >= 7).length}
          </div>
          <div className="stat-label">Strong answers</div>
        </div>
        <div className="card stat-card">
          <div className="stat-value">{data.extracted_skills?.length || 0}</div>
          <div className="stat-label">Skills detected</div>
        </div>
      </section>

      {data.summary && (
        <section className="card assessment-card">
          <h3>Assessment</h3>
          <p>{data.summary}</p>
        </section>
      )}

      <section className="insights-grid">
        {data.strengths?.length > 0 && (
          <div className="card insight-card">
            <h3>Strengths</h3>
            <ul className="insight-list strengths-list">
              {data.strengths.map((strength, index) => (
                <li key={index}>{strength}</li>
              ))}
            </ul>
          </div>
        )}
        {data.improvements?.length > 0 && (
          <div className="card insight-card">
            <h3>Areas for improvement</h3>
            <ul className="insight-list improvements-list">
              {data.improvements.map((item, index) => (
                <li key={index}>{item}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {data.topic_scores && Object.keys(data.topic_scores).length > 0 && (
        <section className="card topic-card">
          <h3>Topic performance</h3>
          <div className="topic-list">
            {Object.entries(data.topic_scores).map(([topic, score]) => (
              <div key={topic} className="topic-row">
                <span>{topic}</span>
                <div className="progress">
                  <div
                    className="progress-bar"
                    style={{
                      width: `${(Number(score) / 10) * 100}%`,
                      background: getScoreColor(Number(score)),
                    }}
                  ></div>
                </div>
                <strong style={{ color: getScoreColor(Number(score)) }}>
                  {Number(score).toFixed(1)}
                </strong>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="qa-timeline">
        <h2>Complete Q&A record</h2>
        {questions.map((question, index) => (
          <article key={index} className="card qa-item">
            <div className="qa-item-header">
              <div className="badge-row">
                <span className="qa-order">Q{question.order}</span>
                <span className="badge badge-accent">{question.topic}</span>
                <span className={`badge badge-${question.difficulty}`}>
                  {question.difficulty}
                </span>
              </div>
              {question.score !== null && question.score !== undefined && (
                <span className="qa-score" style={{ color: getScoreColor(question.score) }}>
                  {question.score}/10
                </span>
              )}
            </div>
            <div className="qa-question">{question.question}</div>
            {question.answer && <div className="qa-answer">{question.answer}</div>}
            {question.feedback && <div className="qa-feedback">{question.feedback}</div>}
          </article>
        ))}
      </section>

      <div className="summary-actions">
        <a href="/" className="btn btn-primary btn-lg">
          Start new interview
        </a>
      </div>
    </main>
  );
}
