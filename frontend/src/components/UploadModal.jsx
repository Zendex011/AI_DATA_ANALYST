import { useState, useRef } from "react";
import Modal from "./Modal.jsx";
import { api, ApiError } from "../api/client.js";

export default function UploadModal({ onClose, onUploaded }) {
  const [file, setFile] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError(null);
    setLoading(true);
    try {
      const result = await api.uploadFile(file);
      onUploaded(result);
    } catch (err) {
      // The backend gives specific, actionable messages for every upload
      // rejection (empty file, bad encoding, duplicate columns, etc.) --
      // surface that text directly rather than a generic "upload failed".
      setError(err instanceof ApiError ? err.detail : "Upload failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Modal title="Upload a CSV" onClose={onClose}>
      <form onSubmit={handleSubmit} className="upload-form">
        <div
          className={`dropzone ${file ? "has-file" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault();
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) setFile(dropped);
          }}
        >
          <input
            ref={inputRef}
            type="file"
            accept=".csv"
            hidden
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
          {file ? (
            <span className="mono">{file.name}</span>
          ) : (
            <span>Click to choose a CSV, or drag one here</span>
          )}
        </div>

        {error && <div className="field-error">{error}</div>}

        <button className="btn btn-primary" type="submit" disabled={!file || loading}>
          {loading ? "Uploading..." : "Upload"}
        </button>
      </form>

      <style>{`
        .upload-form {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .dropzone {
          border: 1px dashed var(--border);
          border-radius: var(--radius);
          padding: 28px 16px;
          text-align: center;
          color: var(--text-muted);
          font-size: 13px;
          transition: border-color 0.15s ease, color 0.15s ease;
        }
        .dropzone:hover {
          border-color: var(--accent);
          color: var(--text);
        }
        .dropzone.has-file {
          border-color: var(--secondary);
          color: var(--text);
        }
      `}</style>
    </Modal>
  );
}
