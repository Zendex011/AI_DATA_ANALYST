import { useState, useEffect, useCallback } from "react";
import Sidebar from "./Sidebar.jsx";
import SourceStatusBar from "./SourceStatusBar.jsx";
import ChatPanel from "./ChatPanel.jsx";
import HistoryPanel from "./HistoryPanel.jsx";
import UploadModal from "./UploadModal.jsx";
import ConnectDbModal from "./ConnectDbModal.jsx";
import { api } from "../api/client.js";

export default function Dashboard() {
  const [files, setFiles] = useState([]);
  const [databases, setDatabases] = useState([]);
  const [loadingSources, setLoadingSources] = useState(true);
  const [selected, setSelected] = useState(null);
  const [view, setView] = useState("chat"); // "chat" | "history"
  const [showUpload, setShowUpload] = useState(false);
  const [showConnect, setShowConnect] = useState(false);

  const refreshSources = useCallback(async () => {
    setLoadingSources(true);
    try {
      const [filesData, dbData] = await Promise.all([api.listFiles(), api.listDatabases()]);
      setFiles(filesData);
      setDatabases(dbData);
    } finally {
      setLoadingSources(false);
    }
  }, []);

  useEffect(() => {
    refreshSources();
  }, [refreshSources]);

  function handleUploaded(result) {
    setShowUpload(false);
    refreshSources().then(() => {
      setSelected({
        type: "csv",
        id: result.file_id,
        label: result.filename,
        meta: { rows: result.rows, columns: result.columns },
      });
      setView("chat");
    });
  }

  function handleConnected(result) {
    setShowConnect(false);
    refreshSources().then(() => {
      setSelected({
        type: "database",
        id: result.db_id,
        label: result.label,
        meta: { dialect: result.dialect },
      });
      setView("chat");
    });
  }

  return (
    <div className="dashboard">
      <Sidebar
        files={files}
        databases={databases}
        selected={selected}
        onSelect={(s) => {
          setSelected(s);
          setView("chat");
        }}
        onUploadClick={() => setShowUpload(true)}
        onConnectClick={() => setShowConnect(true)}
        loading={loadingSources}
      />

      <main className="dashboard-main">
        {!selected ? (
          <div className="dashboard-empty">
            <p>Select a file or database on the left, or add a new one.</p>
          </div>
        ) : (
          <>
            <div className="dashboard-header">
              <SourceStatusBar source={selected} />
              <div className="dashboard-tabs">
                <button
                  className={`dashboard-tab ${view === "chat" ? "active" : ""}`}
                  onClick={() => setView("chat")}
                >
                  Ask
                </button>
                <button
                  className={`dashboard-tab ${view === "history" ? "active" : ""}`}
                  onClick={() => setView("history")}
                >
                  History
                </button>
              </div>
            </div>

            {view === "chat" ? (
              <ChatPanel source={selected} />
            ) : (
              <HistoryPanel source={selected} />
            )}
          </>
        )}
      </main>

      {showUpload && <UploadModal onClose={() => setShowUpload(false)} onUploaded={handleUploaded} />}
      {showConnect && (
        <ConnectDbModal onClose={() => setShowConnect(false)} onConnected={handleConnected} />
      )}

      <style>{`
        .dashboard {
          height: 100%;
          display: flex;
        }
        .dashboard-main {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-width: 0;
        }
        .dashboard-empty {
          margin: auto;
          color: var(--text-muted);
          font-size: 13px;
        }
        .dashboard-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 16px;
        }
        .dashboard-header .status-bar {
          flex: 1;
          margin-right: 0;
        }
        .dashboard-tabs {
          display: flex;
          gap: 4px;
          margin: 16px 20px 0 0;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 3px;
        }
        .dashboard-tab {
          border: none;
          background: transparent;
          color: var(--text-muted);
          padding: 6px 14px;
          border-radius: 4px;
          font-size: 12px;
          font-weight: 500;
        }
        .dashboard-tab.active {
          background: var(--surface-raised);
          color: var(--text);
        }
      `}</style>
    </div>
  );
}
