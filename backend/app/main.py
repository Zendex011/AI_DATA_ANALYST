from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from app.api.routes import router
from app.api.auth_routes import router as auth_router
from app.db.database import engine, Base
from app.db import models  # noqa: F401 -- imported so Base.metadata sees the tables

app = FastAPI(title="AI Data Analyst Agent", version="0.6.0")
# Allow configuring CORS origins via the CORS_ALLOWED_ORIGINS env var
origins = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
allow_origins = [o.strip() for o in origins.split(",") if o.strip()]
print("CORS_ALLOWED_ORIGINS env:", origins)
print("allow_origins:", allow_origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
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