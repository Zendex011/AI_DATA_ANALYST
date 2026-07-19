# AI Data Analyst Agent — Full Phase Breakdown

Each phase is a working, demoable state. Don't start a phase until the
previous one runs end-to-end. A half-built Phase 4 is worth less on a resume
than a fully working Phase 2.

---

## Phase 1 — MVP (already built for you)

**What it does:** User uploads a CSV, asks a question in English, Gemini
generates pandas code, code runs in a sandboxed subprocess, LLM explains the
result in plain English.

**Tech stack:** FastAPI, LangChain, LangGraph, Gemini API, pandas.

**Input:** CSV file (via `/upload`), question string (via `/ask`).

**Output:** JSON with `answer` (plain English), `generated_code`,
`raw_output`.

**Files:** everything already in your zip — `main.py`, `config.py`,
`core/llm.py`, `core/code_executor.py`, `agents/tools.py`,
`agents/orchestrator.py`, `api/routes.py`, `models/schemas.py`.

**What it proves in an interview:** you can wire an LLM to a tool, control
execution, and chain steps with a state graph. That's the core "AI agent"
skill. Nothing else in later phases replaces this — they just add safety,
scale, and persistence around it.

---

## Phase 2 — Persistence (Postgres)

**What it does:** Right now, restart the server and every uploaded file and
every question is gone — `_file_registry` is a Python dict in memory. Phase 2
replaces that with a real database, so uploads and question history survive
restarts and you can list "past analyses."

**New tech stack:** PostgreSQL, SQLAlchemy (ORM), Alembic (migrations).

**Input:** same as Phase 1 (CSV + question), but now also reads/writes to
Postgres.

**Output:** same JSON response, plus new endpoints:
- `GET /files` → list previously uploaded files
- `GET /history/{file_id}` → past questions and answers for a file

**New/changed files:**
```
app/
├── db/
│   ├── database.py       # SQLAlchemy engine + session setup
│   └── models.py         # File, QueryHistory table definitions
├── api/
│   └── routes.py         # updated: reads/writes DB instead of dict
docker-compose.yml         # spins up Postgres locally
alembic/                   # migration scripts
```

**Why this matters:** every real backend needs a persistence layer.
"In-memory dict" is a toy-project smell; a recruiter skimming your code will
notice the difference immediately.

**Watch out for:** don't just dump raw pandas objects into Postgres columns.
Store the file path, metadata (filename, upload time, row/column count), and
query history as text — not the DataFrame itself.

---

## Phase 3 — Real Databases (text-to-SQL)

**What it does:** Right now the tool only works on a single CSV. This phase
lets a user connect an external Postgres/MySQL database (their own), and the
agent generates SQL instead of pandas code when the source is a database.

**New tech stack:** SQLAlchemy reflection (to read table schemas),
`sqlparse` or similar for validating generated SQL before running it.

**Input:** DB connection string (host/user/password, or a connection you
provision for them), question string.

**Output:** same JSON shape, but `generated_code` is now SQL, and
`raw_output` is query results.

**New/changed files:**
```
app/
├── core/
│   └── sql_executor.py     # runs validated, read-only SQL
├── agents/
│   ├── orchestrator.py     # updated: routes to SQL tool or pandas tool
│   └── tools.py            # new: run_sql_query tool
├── models/
│   └── schemas.py          # new: DBConnectionRequest schema
```

**Non-negotiable security requirement:** the DB user your agent connects
with must be **read-only**, and every generated SQL string must be validated
before execution (reject `DROP`, `DELETE`, `UPDATE`, `INSERT`, multiple
statements). This is the part of the whole project most likely to come up in
a security-focused interview question. Don't skip it to save time.

---

## Phase 4 — Charts + Caching

**What it does:** Adds a chart-generation tool (matches the "Generate chart"
node in your original diagram) and Redis caching so identical questions
don't re-hit the Gemini API and re-run code every time.

**New tech stack:** matplotlib or plotly (chart generation), Redis.

**Input:** same question flow; agent now decides whether the answer needs a
chart, a number, or both.

**Output:** JSON now includes an optional `chart_url` or base64-encoded
image, plus a cache flag (`cached: true/false`) so you can show cache hits
in a demo.

**New/changed files:**
```
app/
├── core/
│   ├── chart_generator.py   # builds matplotlib/plotly chart, saves as PNG
│   └── cache.py             # Redis get/set wrapper
├── agents/
│   ├── orchestrator.py      # updated: adds chart-decision node
│   └── tools.py             # new: generate_chart tool
```

**Why Redis specifically:** cache key = hash of (file_id + question).
Second identical question skips the LLM call and the code execution
entirely — this is a genuine performance win you can quantify in an
interview ("cut repeat-query latency from ~3s to ~50ms").

---

## Phase 5 — Hardened Execution (Docker sandbox)

**What it does:** Replaces the subprocess-based code execution from Phase 1
with a real sandbox: each code execution runs inside a short-lived,
resource-limited Docker container with no network access.

**New tech stack:** Docker SDK for Python (`docker-py`), or a lighter
alternative like `firejail` if you don't want to manage container overhead.

**Input/output:** unchanged from the user's perspective — this phase is a
backend hardening exercise, not a feature.

**New/changed files:**
```
app/
├── core/
│   └── code_executor.py    # replaced: spins up Docker container per run
docker/
└── sandbox.Dockerfile       # minimal python+pandas image, no network, non-root user
```

**What changes technically:**
- Container runs with `--network none`, `--memory 256m`, `--cpus 0.5`
- Container filesystem is read-only except a mounted temp directory
- Container is destroyed immediately after execution (no persistence between runs)

**Why this matters:** this is the phase that turns "I called an LLM API"
into "I built a system that safely executes untrusted, LLM-generated code."
That distinction is what separates a tutorial project from an engineering
project.

---

## Phase 6 — Async Jobs + Auth

**What it does:** Two additions that are logically separate but usually
built together: (1) long-running analyses run as background jobs instead of
blocking the HTTP request, (2) multiple users can have accounts, so files
and history are scoped per-user.

**New tech stack:** Celery + Redis (as the broker) for async jobs, JWT
(via `python-jose` or FastAPI's built-in OAuth2 support) for auth.

**Input:** same as before, plus a `Authorization: Bearer <token>` header on
every request; login/signup endpoints added.

**Output:** `/ask` now returns immediately with a `job_id`; a new
`GET /jobs/{job_id}` endpoint returns status (`pending`/`done`) and the
result once ready.

**New/changed files:**
```
app/
├── auth/
│   ├── security.py          # password hashing, JWT creation/verification
│   └── dependencies.py      # get_current_user() FastAPI dependency
├── workers/
│   └── celery_app.py        # Celery app + task definitions
├── api/
│   ├── auth_routes.py       # /signup, /login
│   └── routes.py            # updated: /ask returns job_id, uses Celery task
```

**This is where a task queue is actually justified** — long-running
analysis jobs, need for retries, need for a worker pool. This is also where,
if you still want to make the Kafka case, you'd need multiple independent
consumers acting on the same event (e.g., "job created" triggers logging,
notification, and analytics services separately). If you can't describe
three independent consumers, you don't need Kafka — Celery is the correct
tool here.

---

## Phase 7 — Deployment (optional but strong for a resume)

**What it does:** Packages everything (FastAPI app, Postgres, Redis, Celery
worker) into Docker Compose, adds a basic CI pipeline, and deploys somewhere
public so you can link a live demo, not just a GitHub repo.

**New tech stack:** Docker Compose, GitHub Actions (CI), Render / Railway /
Fly.io / AWS (pick one — don't over-scope this).

**Input/output:** unchanged — this phase is purely operational.

**New/changed files:**
```
docker-compose.yml           # app + postgres + redis + celery worker, one command to run all
.github/workflows/ci.yml     # lint + test on every push
Dockerfile                   # production image for the FastAPI app
```

**Why this matters:** a live, working link beats a repo that requires
someone to clone and configure five environment variables to see it work.
This is often the single highest-leverage phase for actually getting
noticed, and it's frequently skipped because it's "boring." Don't skip it.

---

## Summary table

| Phase | Core addition | Key new tech | Proves |
|---|---|---|---|
| 1 | Agent + sandboxed exec | LangGraph, Gemini, FastAPI | Agent orchestration, tool use |
| 2 | Persistence | Postgres, SQLAlchemy | Data modeling |
| 3 | Real DB connections | Text-to-SQL, query validation | Security-aware design |
| 4 | Charts + caching | matplotlib/plotly, Redis | Multi-tool agents, perf optimization |
| 5 | Hardened sandbox | Docker | Production-grade security |
| 6 | Async + auth | Celery, JWT | Scalable async systems |
| 7 | Deployment | Docker Compose, CI | Shipping, not just coding |

Build and fully test each phase before starting the next. A resume project
that's "Phase 4, partially working" reads worse than one that's "Phase 2,
fully working, live demo link."