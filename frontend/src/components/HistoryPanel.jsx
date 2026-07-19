import { useEffect, useState } from "react";
import { api } from "../api/client.js";

export default function HistoryPanel({ source }) {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const fetcher = source.type === "csv" ? api.getFileHistory(source.id) : api.getDbHistory(source.id);
    fetcher
      .then((data) => {
        if (!cancelled) setHistory(data);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [source.type, source.id]);

  return (
    <div className="history-panel">
      {loading && <p className="history-empty">Loading history...</p>}
      {!loading && history.length === 0 && (
        <p className="history-empty">No questions asked yet for {source.label}.</p>
      )}
      {history.map((h, i) => (
        <div key={i} className={`history-item ${!h.success ? "history-item-error" : ""}`}>
          <div className="history-question mono">{h.question}</div>
          <div className="history-answer">{h.answer}</div>
          <div className="history-meta">
            <span>{new Date(h.created_at).toLocaleString()}</span>
            {h.retries_used > 0 && <span>&middot; {h.retries_used} retry</span>}
            {!h.success && <span className="history-failed">&middot; failed</span>}
          </div>
        </div>
      ))}

      <style>{`
        .history-panel {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .history-empty {
          color: var(--text-muted);
          font-size: 13px;
          margin: auto;
        }
        .history-item {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 14px 16px;
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .history-item-error {
          border-color: var(--danger);
        }
        .history-question {
          font-size: 12px;
          color: var(--accent-strong);
        }
        .history-answer {
          font-size: 13px;
          white-space: pre-wrap;
          line-height: 1.5;
        }
        .history-meta {
          font-size: 11px;
          color: var(--text-faint);
          display: flex;
          gap: 4px;
        }
        .history-failed {
          color: var(--danger);
        }
      `}</style>
    </div>
  );
}
