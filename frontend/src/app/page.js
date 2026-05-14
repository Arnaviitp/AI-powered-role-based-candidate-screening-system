"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ROLE_ICONS = {
  "AI/ML Engineer": "AI",
  "Data Scientist": "DS",
  "Backend Engineer": "BE",
  "Frontend Engineer": "FE",
  "Full Stack Engineer": "FS",
};

export default function Home() {
  const router = useRouter();
  const fileRef = useRef(null);
  const [file, setFile] = useState(null);
  const [role, setRole] = useState("");
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const roles = Object.keys(ROLE_ICONS);

  const handleFile = (selectedFile) => {
    if (!selectedFile) return;
    const isSupported =
      selectedFile.type === "application/pdf" ||
      selectedFile.name.toLowerCase().endsWith(".txt");

    if (!isSupported) {
      setFile(null);
      setError("Please upload a PDF or TXT resume.");
      return;
    }

    setFile(selectedFile);
    setError("");
  };

  const handleSubmit = async () => {
    if (!file) return setError("Please upload your resume.");
    if (!role) return setError("Please select a target role.");

    setLoading(true);
    setError("");

    try {
      const form = new FormData();
      form.append("resume", file);
      form.append("role", role);
      form.append("candidate_name", name.trim() || "Candidate");

      const res = await fetch(`${API}/api/sessions`, {
        method: "POST",
        body: form,
      });

      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(data.detail || "Failed to create the interview session.");
      }

      router.push(`/interview/${data.session_id}`);
    } catch (e) {
      setError(e.message || "Could not reach the backend server.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <main className="container">
        <div className="loading-screen">
          <div className="spinner spinner-lg"></div>
          <h2>Preparing your interview</h2>
          <p>Parsing the resume, building context, and generating questions.</p>
        </div>
      </main>
    );
  }

  return (
    <main className="container">
      <section className="hero animate-fade">
        <div className="hero-kicker">Resume-aware technical interviews</div>
        <h1>
          Screen candidates with structured, role-based AI interviews.
        </h1>
        <p>
          Upload a resume, select the target role, and run an interview with
          generated questions, answer scoring, and a final assessment.
        </p>
      </section>

      {error && <div className="error-alert">{error}</div>}

      <div className="setup-grid animate-slide">
        <section className="card setup-card">
          <label className="label" htmlFor="resume-upload">
            Resume
          </label>
          <button
            type="button"
            className={`upload-zone ${dragOver ? "drag-over" : ""}`}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              handleFile(e.dataTransfer.files[0]);
            }}
            onClick={() => fileRef.current?.click()}
          >
            <span className="upload-icon" aria-hidden="true">
              UP
            </span>
            <span className="upload-title">Drop your resume here</span>
            <span className="upload-subtitle">PDF and TXT files are supported</span>
            <input
              ref={fileRef}
              id="resume-upload"
              type="file"
              accept=".pdf,.txt"
              onChange={(e) => handleFile(e.target.files[0])}
            />
          </button>

          {file && (
            <div className="file-preview">
              <span className="file-icon" aria-hidden="true">
                CV
              </span>
              <div className="file-info">
                <div className="file-name">{file.name}</div>
                <div className="file-size">{(file.size / 1024).toFixed(1)} KB</div>
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setFile(null)}
                type="button"
                aria-label="Remove resume"
              >
                Remove
              </button>
            </div>
          )}

          <div className="field-group">
            <label className="label" htmlFor="candidate-name">
              Candidate name
            </label>
            <input
              id="candidate-name"
              className="input"
              placeholder="John Doe"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
        </section>

        <section className="card setup-card">
          <label className="label">Target role</label>
          <div className="role-grid">
            {roles.map((candidateRole) => (
              <button
                key={candidateRole}
                type="button"
                className={`role-option ${role === candidateRole ? "selected" : ""}`}
                onClick={() => setRole(candidateRole)}
                aria-pressed={role === candidateRole}
              >
                <span className="role-icon" aria-hidden="true">
                  {ROLE_ICONS[candidateRole]}
                </span>
                <span className="role-name">{candidateRole}</span>
              </button>
            ))}
          </div>

          <button
            className="btn btn-primary btn-lg start-button"
            onClick={handleSubmit}
            disabled={!file || !role}
            type="button"
          >
            Start interview
          </button>
        </section>
      </div>

      <section className="feature-strip" aria-label="Application capabilities">
        <span>Resume parsing</span>
        <span>Role-specific questions</span>
        <span>Answer scoring</span>
        <span>Final assessment</span>
      </section>
    </main>
  );
}
