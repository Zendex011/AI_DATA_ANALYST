import { useState } from "react";
import Modal from "./Modal.jsx";
import { api, ApiError } from "../api/client.js";

export default function ConnectDbModal({ onClose, onConnected }) {
  const [label, setLabel] = useState("");
  const [connectionString, setConnectionString] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await api.connectDatabase(connectionString, label);
      onConnected(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not connect. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Connect a database" onClose={onClose}>
      <form onSubmit={handleSubmit} className="connect-form">
        <div className="field">
          <label htmlFor="label">Label</label>
          <input
            id="label"
            required
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Production analytics"
          />
        </div>
        <div className="field">
          <label htmlFor="conn">Connection string</label>
          <input
            id="conn"
            required
            className="mono"
            value={connectionString}
            onChange={(e) => setConnectionString(e.target.value)}
            placeholder="postgresql://user:pass@host:5432/dbname"
          />
        </div>

        <p className="connect-note">
          Use a <strong>read-only</strong> database user. The backend validates every generated
          query and rejects anything that isn't a SELECT, but that's defense-in-depth, not a
          substitute for real read-only credentials.
        </p>

        {error && <div className="field-error">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={loading}>
          {loading ? "Connecting..." : "Connect"}
        </button>
      </form>

      <style>{`
        .connect-form {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .connect-note {
          font-size: 12px;
          color: var(--text-muted);
          background: var(--bg);
          border: 1px solid var(--border-soft);
          border-radius: var(--radius);
          padding: 10px 12px;
          margin: 0;
          line-height: 1.5;
        }
      `}</style>
    </Modal>
  );
}
