# AI Data Analyst — Frontend

React (Vite) frontend for the AI Data Analyst backend. Covers everything
the backend supports: auth, CSV upload, database connections, chat-style
questions with optional charts, and history.

## Setup

```bash
cd frontend
npm install
cp .env.example .env   # only needed if your backend isn't on localhost:8000
npm run dev
```

Open http://localhost:5173. Your backend must already be running on
`http://localhost:8000` (or whatever you set `VITE_API_BASE_URL` to) —
see the backend's own README for how to start it.

**Also make sure the backend's CORS setting allows this origin.** By
default `CORS_ALLOWED_ORIGINS` in the backend's `.env` already includes
`http://localhost:5173`, so this works out of the box for local dev. If
you deploy the frontend somewhere else, add that real origin to the
backend's `CORS_ALLOWED_ORIGINS` or requests will be silently blocked by
the browser (you'll see a CORS error in devtools, not a normal HTTP error).

## What's built

- **Auth** — signup/login, JWT stored in `localStorage` (this is a real
  standalone app, not a Claude.ai artifact, so `localStorage` is the
  correct choice here — token persists across page refreshes)
- **Files** — upload CSVs, see them listed in the sidebar with row/column counts
- **Databases** — connect a database by connection string, see the schema
  reflected back, ask questions against it
- **Chat** — ask questions in plain English against whichever source is
  selected; toggle "Chart" to request a visualization; expandable "Show
  Python"/"Show SQL" reveals exactly what ran; SQL questions also get a
  "View data" toggle showing the actual result rows
- **History** — past questions and answers per source, including failed
  attempts (shown distinctly)

## Deliberate scope decisions

- **Async jobs (`/ask-async`, `/jobs/{id}`) are NOT wired into the UI.**
  The backend supports them, but a polling UI (progress states, retry,
  cancel) is a meaningfully separate feature from the rest of this build.
  The synchronous `/ask` and `/ask-db` endpoints are used instead, which
  is fine for typical question latency. Say the word if you want the
  async path wired in — it's a real addition, not a toggle.
- **No routing library.** This is a single-page dashboard (sidebar +
  main panel), so view switching is done with component state
  (`selected source` + `chat`/`history` tab) rather than adding
  `react-router-dom` for a page structure that doesn't have real pages.
- **No component library / Tailwind.** Plain CSS with a token system
  (see `src/index.css`) — kept dependencies minimal and the design
  intentional rather than defaulting to whatever a component library
  ships with.

## Verification note

This was built and then actually driven through a real headless browser
(Playwright, used only for my own verification — it's not a project
dependency) against the real backend with a mocked LLM: signup, upload,
ask, chart rendering, code toggle, history, logout, wrong-password error
display, and the full database-connect-and-query flow including the data
table view. A real race condition (dashboard fetching data before the auth
token was synced, causing spurious 401s right after login) was caught this
way and fixed. Screenshots were reviewed to confirm the design actually
renders as intended, not just that the build succeeds.

What wasn't independently re-verified: production behavior at real scale
(large CSVs, many concurrent users), and any browser other than Chromium.
