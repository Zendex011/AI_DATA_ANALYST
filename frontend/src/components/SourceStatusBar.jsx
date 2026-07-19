export default function SourceStatusBar({ source }) {
  if (!source) return null;

  const isCsv = source.type === "csv";
  const meta = source.meta;

  return (
    <div className="status-bar">
      <div className="status-pulse" />
      <div className="status-field">
        <span className="status-label">source</span>
        <span className="status-value mono">{source.label}</span>
      </div>
      {isCsv ? (
        <>
          <div className="status-divider" />
          <div className="status-field">
            <span className="status-label">rows</span>
            <span className="status-value mono">{meta.rows.toLocaleString()}</span>
          </div>
          <div className="status-divider" />
          <div className="status-field status-field-grow">
            <span className="status-label">columns</span>
            <span className="status-value mono status-columns">{meta.columns.join(", ")}</span>
          </div>
        </>
      ) : (
        <>
          <div className="status-divider" />
          <div className="status-field">
            <span className="status-label">dialect</span>
            <span className="status-value mono">{meta.dialect}</span>
          </div>
        </>
      )}

      <style>{`
        .status-bar {
          display: flex;
          align-items: center;
          gap: 16px;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 10px 16px;
          margin: 16px 20px 0;
        }
        .status-pulse {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--secondary);
          box-shadow: 0 0 6px var(--secondary);
          animation: status-pulse 2s ease-in-out infinite;
          flex-shrink: 0;
        }
        @keyframes status-pulse {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
        .status-field {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-width: 0;
        }
        .status-field-grow {
          flex: 1;
          min-width: 0;
        }
        .status-label {
          font-size: 10px;
          color: var(--text-faint);
          text-transform: uppercase;
          letter-spacing: 0.07em;
        }
        .status-value {
          font-size: 12px;
          color: var(--text);
          font-variant-numeric: tabular-nums;
        }
        .status-columns {
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .status-divider {
          width: 1px;
          height: 24px;
          background: var(--border-soft);
          flex-shrink: 0;
        }
      `}</style>
    </div>
  );
}
