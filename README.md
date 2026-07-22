  # AI Data Analyst Agent (https://ai-data-analyst-seven-dusky.vercel.app/)

A FastAPI + LangGraph application that lets you:
- upload a CSV and ask questions in plain English
- connect to an external database and ask SQL-based questions
- inspect uploaded files and prior query history
- optionally generate charts from supported results

The app uses Gemini to generate either pandas code or SQL, then executes it and returns a response with the generated code/query and any execution output.

## Current capabilities

- FastAPI back  end with Swagger docs at `/docs`
- CSV workflow via `/upload` and `/ask`
- Database workflow via `/connect-db` and `/ask-db`
- File and history endpoints for both CSV and database sessions
- Local SQLite persistence by default, with optional Postgres and Redis support via Docker Compose
- Optional chart generation for supported responses


## Environment variables

The app reads these variables from the backend `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here
MAX_CODE_EXEC_SECONDS=10
UPLOAD_DIR=./uploads
DATABASE_URL=sqlite:///./app_data.db     # optional override
REDIS_URL=redis://localhost:6379/0      # optional override
```

If `GEMINI_API_KEY` is missing, the app starts with a warning and downstream LLM calls will fail until it is set.

## Optional services with Docker Compose

The repository includes a Docker Compose setup for Postgres and Redis:

```bash
docker compose up -d postgres redis
```

This is useful when you want to test the app with a more realistic persistence/cache setup instead of the default local SQLite and in-process cache behavior.

## Example API calls

### Upload a CSV

```bash
curl -X POST http://localhost:8000/upload \
  -F "file=@your_data.csv"
```

### Ask a question about the uploaded CSV

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "file_id": "PASTE_FILE_ID_HERE",
    "question": "What is the average value in the price column?"
  }'
```

### Connect a database

```bash
curl -X POST http://localhost:8000/connect-db \
  -H "Content-Type: application/json" \
  -d '{
    "label": "Local Postgres",
    "connection_string": "postgresql://user:password@localhost:5432/dbname"
  }'
```

### Ask a question about the connected database

```bash
curl -X POST http://localhost:8000/ask-db \
  -H "Content-Type: application/json" \
  -d '{
    "db_id": "PASTE_DB_ID_HERE",
    "question": "Show the top 5 customers by total spend"
  }'
```

### List files and history

```bash
curl http://localhost:8000/files
curl http://localhost:8000/history/PASTE_FILE_ID_HERE
curl http://localhost:8000/history-db/PASTE_DB_ID_HERE
```

## Project structure

```text
ai-data-analyst/
├── README.md
├── docker-compose.yml
├── backend/
│   ├── requirements.txt
│   ├── .env.example
│   ├── uploads/
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── agents/
│       │   ├── orchestrator.py
│       │   └── sql_orchestrator.py
│       ├── api/
│       │   └── routes.py
│       ├── core/
│       │   ├── cache.py
│       │   ├── chart_generator.py
│       │   ├── code_executor.py
│       │   ├── db_schema.py
│       │   ├── llm.py
│       │   ├── sql_executor.py
│       │   ├── sql_validator.py
│       │   └── schema_utils.py
│       ├── db/
│       │   ├── database.py
│       │   └── models.py
│       └── models/
│           └── schemas.py
```

## Notes and limitations

- The code-execution path uses a subprocess with a timeout and is not a hardened sandbox. It should not be exposed to untrusted users.
- The default database is SQLite for local development. Postgres is available as an optional upgrade path via Docker Compose.
- Redis caching is optional; if it is unavailable, the app gracefully treats cache misses as normal.
- No frontend is included in this repository; use the Swagger UI or curl for interaction.
