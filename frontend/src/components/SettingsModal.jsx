import { useState, useEffect } from "react";
import Modal from "./Modal.jsx";
import { api, ApiError } from "../api/client.js";

export default function SettingsModal({ onClose }) {
  const [hasCustomKey, setHasCustomKey] = useState(null); // null = still loading
  const [keyInput, setKeyInput] = useState("");
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.getApiKeyStatus().then((data) => setHasCustomKey(data.has_custom_key));
  }, []);

  async function handleSave(e) {
    e.preventDefault();
    if (!keyInput.trim()) return;
    setError(null);
    setSaving(true);
    try {
      await api.setApiKey(keyInput.trim());
      setHasCustomKey(true);
      setKeyInput("");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not save the key. Try again.");
    } finally {
      setSaving(false);
    }
  }

  async function handleRemove() {
    setError(null);
    setSaving(true);
    try {
      await api.deleteApiKey();
      setHasCustomKey(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Could not remove the key. Try again.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Modal title="Your Gemini API key" onClose={onClose}>
      <div className="settings-body">
        {hasCustomKey === null && <p className="settings-note">Loading...</p>}

        {hasCustomKey !== null && (
          <div className={`settings-status ${hasCustomKey ? "settings-status-active" : ""}`}>
            <span className="settings-status-dot" />
            {hasCustomKey
              ? "You're using your own Gemini API key."
              : "You're using the app's shared key."}
          </div>
        )}

        <p className="settings-note">
          Add your own key so your questions bill to your own Google account instead of the app
          owner's. Your key is encrypted at rest and is never shown back to you or anyone else once
          saved.
        </p>

        <form onSubmit={handleSave} className="settings-form">
          <div className="field">
            <label htmlFor="apiKey">Gemini API key</label>
            <input
              id="apiKey"
              type="password"
              className="mono"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="AIza..."
              autoComplete="off"
            />
          </div>

          {error && <div className="field-error">{error}</div>}

          <div className="settings-actions">
            <button className="btn btn-primary" type="submit" disabled={saving || !keyInput.trim()}>
              {saving ? "Saving..." : "Save key"}
            </button>
            {hasCustomKey && (
              <button
                type="button"
                className="btn btn-danger-outline"
                onClick={handleRemove}
                disabled={saving}
              >
                Remove my key
              </button>
            )}
          </div>
        </form>
      </div>

      <style>{`
        .settings-body {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .settings-status {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 12px;
          color: var(--text-muted);
        }
        .settings-status-dot {
          width: 7px;
          height: 7px;
          border-radius: 50%;
          background: var(--text-faint);
        }
        .settings-status-active {
          color: var(--secondary);
        }
        .settings-status-active .settings-status-dot {
          background: var(--secondary);
          box-shadow: 0 0 5px var(--secondary);
        }
        .settings-note {
          font-size: 12px;
          color: var(--text-muted);
          line-height: 1.5;
          margin: 0;
        }
        .settings-form {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .settings-actions {
          display: flex;
          gap: 10px;
        }
      `}</style>
    </Modal>
  );
}
