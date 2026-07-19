from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.db.database import engine, Base
from app.db import models  # noqa: F401 -- imported so Base.metadata sees the tables

app = FastAPI(title="AI Data Analyst Agent", version="0.6.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(router)


@app.on_event("startup")
def create_tables():
    # create_all() only creates tables that don't already exist — safe to
    # run every startup. This is fine for two tables at this stage; once the
    # schema needs versioned changes, switch to Alembic migrations instead.
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def health():
    return {"status": "ok"}