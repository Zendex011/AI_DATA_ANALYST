import { useState } from "react";

function AssistantMessage({ response }) {
  const [showCode, setShowCode] = useState(false);
  const [showData, setShowData] = useState(false);

  const isDb = "generated_sql" in response;
  const code = isDb ? response.generated_sql : response.generated_code;
  const codeLabel = isDb ? "SQL" : "Python";

  return (
    <div className={`msg msg-assistant ${!response.success ? "msg-error" : ""}`}>
      <div className="msg-bubble">
        {response.cached && <span className="msg-badge">cached</span>}

        <p className="msg-answer">{response.answer}</p>

        {(response.chart_url || response.chart_base64) && (
          <img
            className="msg-chart"
            src={
                response.chart_base64
                ? `data:image/png;base64,${response.chart_base64}`
                : `${import.meta.env.VITE_API_URL}${response.chart_url}`
        }
          alt="Generated chart"
        />
        )}
        {response.chart_error && (
          <div className="msg-chart-error">Chart couldn't be generated: {response.chart_error}</div>
        )}

        {isDb && response.rows?.length > 0 && (
          <button className="msg-toggle" onClick={() => setShowData((v) => !v)}>
            {showData ? "Hide" : "View"} data ({response.row_count} row
            {response.row_count === 1 ? "" : "s"}
            {response.truncated ? "+" : ""})
          </button>
        )}
        {isDb && showData && (
          <div className="msg-table-wrap">
            <table className="msg-table mono">
              <thead>
                <tr>
                  {response.columns.map((c) => (
                    <th key={c}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {response.rows.slice(0, 50).map((row, i) => (
                  <tr key={i}>
                    {row.map((cell, j) => (
                      <td key={j}>{String(cell)}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {code && (
          <button className="msg-toggle" onClick={() => setShowCode((v) => !v)}>
            {showCode ? "Hide" : "Show"} {codeLabel}
          </button>
        )}
        {showCode && <pre className="msg-code mono">{code}</pre>}
      </div>

      <style>{`
        .msg { display: flex; }
        .msg-assistant { justify-content: flex-start; }
        .msg-bubble {
          max-width: 640px;
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 14px 16px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .msg-error .msg-bubble {
          border-color: var(--danger);
          background: var(--danger-dim);
        }
        .msg-badge {
          align-self: flex-start;
          font-size: 10px;
          text-transform: uppercase;
          letter-spacing: 0.05em;
          color: var(--secondary);
          border: 1px solid var(--secondary-dim);
          background: var(--secondary-dim);
          border-radius: 4px;
          padding: 2px 6px;
        }
        .msg-answer {
          margin: 0;
          white-space: pre-wrap;
          font-size: 13.5px;
          line-height: 1.6;
        }
        .msg-chart {
          max-width: 100%;
          border-radius: var(--radius);
          border: 1px solid var(--border-soft);
        }
        .msg-chart-error {
          font-size: 12px;
          color: var(--danger);
        }
        .msg-toggle {
          align-self: flex-start;
          background: transparent;
          border: none;
          color: var(--accent);
          font-size: 12px;
          font-weight: 500;
          padding: 0;
        }
        .msg-toggle:hover {
          color: var(--accent-strong);
        }
        .msg-code {
          background: var(--bg);
          border: 1px solid var(--border-soft);
          border-radius: var(--radius);
          padding: 12px;
          font-size: 12px;
          overflow-x: auto;
          margin: 0;
          white-space: pre;
        }
        .msg-table-wrap {
          overflow-x: auto;
          border: 1px solid var(--border-soft);
          border-radius: var(--radius);
          max-height: 260px;
          overflow-y: auto;
        }
        .msg-table {
          border-collapse: collapse;
          font-size: 12px;
          width: 100%;
        }
        .msg-table th, .msg-table td {
          padding: 6px 10px;
          border-bottom: 1px solid var(--border-soft);
          text-align: left;
          white-space: nowrap;
        }
        .msg-table th {
          color: var(--text-muted);
          font-weight: 500;
          position: sticky;
          top: 0;
          background: var(--surface);
        }
      `}</style>
    </div>
  );
}

export default function ChatMessage({ message }) {
  if (message.role === "user") {
    return (
      <div className="msg msg-user">
        <div className="msg-bubble-user">{message.question}</div>
        <style>{`
          .msg-user { justify-content: flex-end; }
          .msg-bubble-user {
            max-width: 640px;
            background: var(--accent-dim);
            border: 1px solid var(--accent);
            color: var(--text);
            border-radius: var(--radius-lg);
            padding: 10px 16px;
            font-size: 13.5px;
          }
        `}</style>
      </div>
    );
  }
  return <AssistantMessage response={message.response} />;
}
