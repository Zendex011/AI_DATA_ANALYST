import { useState, useRef, useEffect } from "react";
import ChatMessage from "./ChatMessage.jsx";
import Spinner from "./Spinner.jsx";
import { api, ApiError } from "../api/client.js";

export default function ChatPanel({ source }) {
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [includeChart, setIncludeChart] = useState(false);
  const [asking, setAsking] = useState(false);
  const scrollRef = useRef(null);

  // Fresh conversation each time the selected source changes -- a chat
  // thread about file A shouldn't linger when you switch to database B.
  useEffect(() => {
    setMessages([]);
  }, [source?.type, source?.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, asking]);

  async function handleAsk(e) {
    e.preventDefault();
    const q = question.trim();
    if (!q || asking) return;

    setMessages((prev) => [...prev, { role: "user", question: q }]);
    setQuestion("");
    setAsking(true);

    try {
      const response =
        source.type === "csv"
          ? await api.askFile(source.id, q, includeChart)
          : await api.askDatabase(source.id, q, includeChart);
      setMessages((prev) => [...prev, { role: "assistant", response }]);
    } catch (err) {
      const detail = err instanceof ApiError ? err.detail : "Something went wrong asking that.";
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          response: { answer: detail, success: false, generated_code: "", stdout: "" },
        },
      ]);
    } finally {
      setAsking(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-scroll" ref={scrollRef}>
        {messages.length === 0 && (
          <div className="chat-empty">
            <p>Ask something about {source.label}.</p>
            <p className="chat-empty-sub">
              {source.type === "csv"
                ? 'Try: "What\'s the average of [a column]?" or "Show me the top 5 rows by [column]."'
                : 'Try: "How many rows are in [a table]?" or "What\'s the distribution of [a column]?"'}
            </p>
          </div>
        )}
        {messages.map((m, i) => (
          <ChatMessage key={i} message={m} />
        ))}
        {asking && (
          <div className="msg msg-assistant">
            <div className="msg-bubble-loading">
              <Spinner label="Thinking..." />
            </div>
          </div>
        )}
      </div>

      <form className="chat-composer" onSubmit={handleAsk}>
        <label className="chat-chart-toggle">
          <input
            type="checkbox"
            checked={includeChart}
            onChange={(e) => setIncludeChart(e.target.checked)}
          />
          Chart
        </label>
        <input
          className="chat-input"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask a question about this data..."
          disabled={asking}
        />
        <button className="btn btn-primary" type="submit" disabled={asking || !question.trim()}>
          Ask
        </button>
      </form>

      <style>{`
        .chat-panel {
          flex: 1;
          display: flex;
          flex-direction: column;
          min-height: 0;
        }
        .chat-scroll {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 14px;
        }
        .chat-empty {
          margin: auto;
          text-align: center;
          color: var(--text-muted);
        }
        .chat-empty p { margin: 4px 0; font-size: 13px; }
        .chat-empty-sub { color: var(--text-faint); font-size: 12px; max-width: 380px; }
        .msg-bubble-loading {
          background: var(--surface);
          border: 1px solid var(--border);
          border-radius: var(--radius-lg);
          padding: 12px 16px;
        }
        .chat-composer {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 14px 20px;
          border-top: 1px solid var(--border);
          background: var(--surface);
        }
        .chat-chart-toggle {
          display: flex;
          align-items: center;
          gap: 6px;
          font-size: 12px;
          color: var(--text-muted);
          white-space: nowrap;
          flex-shrink: 0;
        }
        .chat-input {
          flex: 1;
          background: var(--bg);
          border: 1px solid var(--border);
          border-radius: var(--radius);
          padding: 10px 14px;
          color: var(--text);
        }
        .chat-input:focus {
          border-color: var(--accent);
        }
      `}</style>
    </div>
  );
}
