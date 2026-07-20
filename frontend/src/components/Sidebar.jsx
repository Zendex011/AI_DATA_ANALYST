import { useAuth } from "../context/AuthContext.jsx";

export default function Sidebar({
  files,
  databases,
  selected,
  onSelect,
  onUploadClick,
  onConnectClick,
  onSettingsClick,
  loading,
}) {
  const { email, logout } = useAuth();

  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <span className="sidebar-brand-dot" />
        <span className="sidebar-brand-name">AI Data Analyst</span>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-head">
          <span>Files</span>
          <button className="btn btn-ghost sidebar-add" onClick={onUploadClick} title="Upload a CSV">
            +
          </button>
        </div>
        <div className="sidebar-list">
          {loading && <div className="sidebar-empty">Loading...</div>}
          {!loading && files.length === 0 && (
            <div className="sidebar-empty">No files yet. Upload a CSV to get started.</div>
          )}
          {files.map((f) => (
            <button
              key={f.file_id}
              className={`sidebar-item ${
                selected?.type === "csv" && selected.id === f.file_id ? "active" : ""
              }`}
              onClick={() => onSelect({ type: "csv", id: f.file_id, label: f.filename, meta: f })}
            >
              <span className="sidebar-item-name">{f.filename}</span>
              <span className="sidebar-item-sub mono">{f.rows} rows</span>
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-section">
        <div className="sidebar-section-head">
          <span>Databases</span>
          <button
            className="btn btn-ghost sidebar-add"
            onClick={onConnectClick}
            title="Connect a database"
          >
            +
          </button>
        </div>
        <div className="sidebar-list">
          {!loading && databases.length === 0 && (
            <div className="sidebar-empty">No databases connected yet.</div>
          )}
          {databases.map((d) => (
            <button
              key={d.db_id}
              className={`sidebar-item ${
                selected?.type === "database" && selected.id === d.db_id ? "active" : ""
              }`}
              onClick={() => onSelect({ type: "database", id: d.db_id, label: d.label, meta: d })}
            >
              <span className="sidebar-item-name">{d.label}</span>
              <span className="sidebar-item-sub mono">{d.dialect}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        <span className="sidebar-user mono">{email}</span>
        <div className="sidebar-footer-actions">
          <button
            className="btn btn-ghost sidebar-settings"
            onClick={onSettingsClick}
            title="Manage your Gemini API key"
          >
            Settings
          </button>
          <button className="btn btn-ghost sidebar-logout" onClick={logout}>
            Log out
          </button>
        </div>
      </div>

      <style>{`
        .sidebar {
          width: 260px;
          flex-shrink: 0;
          background: var(--surface);
          border-right: 1px solid var(--border);
          display: flex;
          flex-direction: column;
          height: 100%;
        }
        .sidebar-brand {
          display: flex;
          align-items: center;
          gap: 8px;
          padding: 18px 16px;
          border-bottom: 1px solid var(--border-soft);
        }
        .sidebar-brand-dot {
          width: 8px;
          height: 8px;
          border-radius: 50%;
          background: var(--accent);
          box-shadow: 0 0 6px var(--accent);
        }
        .sidebar-brand-name {
          font-family: var(--font-display);
          font-weight: 600;
          font-size: 14px;
        }
        .sidebar-section {
          padding: 14px 12px 4px;
        }
        .sidebar-section-head {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 0 4px 8px;
          color: var(--text-muted);
          font-size: 11px;
          font-weight: 600;
          text-transform: uppercase;
          letter-spacing: 0.06em;
        }
        .sidebar-add {
          padding: 0 6px;
          font-size: 15px;
          line-height: 1;
          border-radius: 4px;
        }
        .sidebar-list {
          display: flex;
          flex-direction: column;
          gap: 2px;
          min-height: 20px;
        }
        .sidebar-empty {
          color: var(--text-faint);
          font-size: 12px;
          padding: 8px 4px;
        }
        .sidebar-item {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 2px;
          width: 100%;
          text-align: left;
          border: 1px solid transparent;
          background: transparent;
          border-radius: var(--radius);
          padding: 8px 10px;
        }
        .sidebar-item:hover {
          background: var(--surface-raised);
        }
        .sidebar-item.active {
          background: var(--accent-dim);
          border-color: var(--accent);
        }
        .sidebar-item-name {
          font-size: 13px;
          font-weight: 500;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          max-width: 100%;
        }
        .sidebar-item-sub {
          font-size: 11px;
          color: var(--text-muted);
        }
        .sidebar-footer {
          margin-top: auto;
          border-top: 1px solid var(--border-soft);
          padding: 12px 16px;
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 8px;
        }
        .sidebar-footer-actions {
          display: flex;
          gap: 4px;
          flex-shrink: 0;
        }
        .sidebar-settings {
          font-size: 12px;
          padding: 4px 8px;
        }
        .sidebar-user {
          font-size: 11px;
          color: var(--text-muted);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .sidebar-logout {
          font-size: 12px;
          padding: 4px 8px;
          flex-shrink: 0;
        }
      `}</style>
    </aside>
  );
}
