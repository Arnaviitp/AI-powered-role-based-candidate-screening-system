"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ROLE_ICONS = {
  "AI/ML Engineer": "AI",
  "Data Scientist": "DS",
  "Backend Engineer": "BE",
  "Frontend Engineer": "FE",
  "Full Stack Engineer": "FS",
};

export default function DashboardPage() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API}/api/sessions`)
      .then((r) => {
        if (!r.ok) throw new Error("Failed to load sessions.");
        return r.json();
      })
      .then((data) => setSessions(Array.isArray(data) ? data : []))
      .catch((err) => {
        setError(err.message || "Could not reach the backend server.");
        setSessions([]);
      })
      .finally(() => setLoading(false));
  }, []);

  const getScoreColor = (score) =>
    score >= 8 ? "var(--success)" : score >= 5 ? "var(--warning)" : "var(--danger)";

  const formatDate = (iso) => {
    if (!iso) return "Unknown date";
    const date = new Date(iso);
    if (Number.isNaN(date.getTime())) return "Unknown date";
    return date.toLocaleString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const handleDelete = async (event, id) => {
    event.preventDefault();
    event.stopPropagation();

    if (!confirm("Delete this session?")) return;

    try {
      const res = await fetch(`${API}/api/sessions/${id}`, { method: "DELETE" });
      if (!res.ok) throw new Error("Delete failed.");
      setSessions((prev) => prev.filter((session) => session.id !== id));
    } catch (err) {
      setError(err.message || "Unable to delete the session.");
    }
  };

  if (loading) {
    return (
      <main className="container">
        <div className="loading-screen">
          <div className="spinner spinner-lg"></div>
          <h2>Loading sessions</h2>
        </div>
      </main>
    );
  }

  return (
    <main className="container animate-fade">
      <div className="dashboard-header">
        <h1>Interview sessions</h1>
        <p>
          {sessions.length} session{sessions.length !== 1 ? "s" : ""} recorded
        </p>
      </div>

      {error && <div className="error-alert">{error}</div>}

      {sessions.length === 0 ? (
        <section className="empty-state">
          <div className="empty-icon" aria-hidden="true">
            0
          </div>
          <h3>No sessions yet</h3>
          <p>Start your first AI-powered interview to see results here.</p>
          <a href="/" className="btn btn-primary empty-action">
            Start interview
          </a>
        </section>
      ) : (
        <div className="sessions-list">
          {sessions.map((session) => {
            const href =
              session.status === "completed"
                ? `/summary/${session.id}`
                : `/interview/${session.id}`;

            return (
              <a key={session.id} href={href} className="session-link">
                <article className="card session-card">
                  <div>
                    <div className="session-title">
                      <span className="role-chip" aria-hidden="true">
                        {ROLE_ICONS[session.role] || "RL"}
                      </span>
                      <strong>{session.candidate_name || "Anonymous"}</strong>
                    </div>
                    <div className="session-meta">
                      <span className="badge badge-accent">{session.role}</span>
                      <span className="status-label">
                        <span className={`status-dot ${session.status}`}></span>
                        {session.status === "completed" ? "Completed" : "In progress"}
                      </span>
                      <span>{formatDate(session.created_at)}</span>
                    </div>
                  </div>

                  <div className="session-actions">
                    {session.overall_score != null && (
                      <div
                        className="session-score"
                        style={{ color: getScoreColor(session.overall_score) }}
                      >
                        {Number(session.overall_score).toFixed(1)}
                        <small>/10</small>
                      </div>
                    )}
                    <button
                      className="btn btn-ghost btn-sm danger-button"
                      onClick={(event) => handleDelete(event, session.id)}
                      type="button"
                    >
                      Delete
                    </button>
                  </div>
                </article>
              </a>
            );
          })}
        </div>
      )}
    </main>
  );
}
