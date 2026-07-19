export default function Spinner({ label }) {
  return (
    <div className="spinner-row">
      <span className="spinner-dot" />
      <span className="spinner-dot" />
      <span className="spinner-dot" />
      {label && <span className="spinner-label">{label}</span>}
      <style>{`
        .spinner-row {
          display: flex;
          align-items: center;
          gap: 5px;
        }
        .spinner-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: var(--accent);
          animation: spinner-pulse 1.1s ease-in-out infinite;
        }
        .spinner-dot:nth-child(2) { animation-delay: 0.15s; }
        .spinner-dot:nth-child(3) { animation-delay: 0.3s; }
        .spinner-label {
          margin-left: 6px;
          color: var(--text-muted);
          font-size: 13px;
        }
        @keyframes spinner-pulse {
          0%, 80%, 100% { opacity: 0.25; transform: scale(0.85); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  );
}
