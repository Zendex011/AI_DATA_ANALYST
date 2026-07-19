import { useState } from "react";
import { useAuth, ApiError } from "../context/AuthContext.jsx";

export default function AuthPage() {
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login"); // "login" | "signup"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") {
        await login(email, password);
      } else {
        await signup(email, password);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Something went wrong. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-brand">
          <span className="auth-brand-dot" />
          <span className="auth-brand-name">AI Data Analyst</span>
        </div>
        <p className="auth-tagline">Upload a dataset or connect a database. Ask in plain English.</p>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${mode === "login" ? "active" : ""}`}
            onClick={() => setMode("login")}
            type="button"
          >
            Log in
          </button>
          <button
            className={`auth-tab ${mode === "signup" ? "active" : ""}`}
            onClick={() => setMode("signup")}
            type="button"
          >
            Sign up
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="field">
            <label htmlFor="email">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              placeholder="you@example.com"
            />
          </div>
          <div className="field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder="At least 8 characters"
            />
          </div>

          {error && <div className="field-error">{error}</div>}

          <button className="btn btn-primary auth-submit" type="submit" disabled={loading}>
            {loading ? "Working..." : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
      </div>

      <style>{`
        .auth-page {
          height: 100%;
          display: flex;
          align-items: center;
          justify-content: center;
          background:
            radial-gradient(circle at 20% 20%, rgba(232, 163, 61, 0.06), transparent 40%),
            radial-gradient(circle at 80% 80%, rgba(79, 184, 168, 0.06), transparent 40%),
            var(--bg);
        }
        .auth-card {
          width: 380px;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 32px;
        }
        .auth-brand {
          display: flex;
          align-items: center;
          gap: 10px;
          margin-bottom: 8px;
        }
        .auth-brand-dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 8px var(--accent);
        }
        .auth-brand-name {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 18px;
          letter-spacing: -0.01em;
        }
        .auth-tagline {
          color: var(--text-muted);
          font-size: 13px;
          margin: 0 0 24px 0;
        }
        .auth-tabs {
          display: flex;
          gap: 4px;
          background: var(--bg);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 3px;
          margin-bottom: 20px;
        }
        .auth-tab {
          flex: 1;
          border: none;
          background: transparent;
          color: var(--text-muted);
          padding: 8px;
          border-radius: 4px;
          font-weight: 500;
          font-size: 13px;
        }
        .auth-tab.active {
          background: var(--surface-raised);
          color: var(--text);
        }
        .auth-form {
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .auth-submit {
          margin-top: 4px;
          padding: 10px;
        }
      `}</style>
    </div>
  );
}
