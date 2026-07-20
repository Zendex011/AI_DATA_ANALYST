import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.database import Base


def gen_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=gen_uuid)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    # Encrypted (see app/core/crypto.py), never stored in plaintext. NULL
    # means the user hasn't set their own key -- falls back to the app's
    # global GEMINI_API_KEY.
    gemini_api_key = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("UploadedFile", back_populates="owner", cascade="all, delete-orphan")
    databases = relationship("DatabaseConnection", back_populates="owner", cascade="all, delete-orphan")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id = Column(String, primary_key=True, default=gen_uuid)
    # Nullable so existing pre-auth rows (from Phases 1-5) don't violate a
    # NOT NULL constraint the moment this column is added to an existing
    # database. Practically, an unowned file is invisible to every user --
    # see the migration note in the routes for how to handle that.
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    filename = Column(String, nullable=False)
    path = Column(String, nullable=False)
    rows = Column(Integer, nullable=False)
    # Stored as a comma-joined string rather than a JSON column: keeps this
    # table portable across SQLite (dev) and Postgres (prod) without relying
    # on a Postgres-only JSONB type. Fine for a column list; revisit if you
    # ever need to query inside this field.
    columns = Column(Text, nullable=False)
    # JSON string: {"col_name": "int64", ...}. Computed once at upload time
    # so /ask never has to re-read the CSV just to know column types.
    dtypes = Column(Text, nullable=False, default="{}")
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="files")
    queries = relationship(
        "QueryHistory", back_populates="file", cascade="all, delete-orphan"
    )

    def columns_list(self) -> list[str]:
        return self.columns.split(",") if self.columns else []


class QueryHistory(Base):
    """
    Covers both CSV questions (source_type="csv", file_id set, db_id null)
    and database questions (source_type="database", db_id set, file_id
    null). generated_code holds pandas code for CSV rows and SQL for
    database rows -- same column, different content, distinguished by
    source_type. Kept as one column rather than two (generated_code /
    generated_sql) to avoid a schema with a permanently-null column on
    every row.
    """
    __tablename__ = "query_history"

    id = Column(String, primary_key=True, default=gen_uuid)
    source_type = Column(String, nullable=False)  # "csv" or "database"
    file_id = Column(String, ForeignKey("uploaded_files.id"), nullable=True)
    db_id = Column(String, ForeignKey("database_connections.id"), nullable=True)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    generated_code = Column(Text, nullable=False)
    success = Column(Boolean, nullable=False)
    error_type = Column(String, nullable=True)
    error_message = Column(Text, nullable=True)
    retries_used = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    file = relationship("UploadedFile", back_populates="queries")
    database = relationship("DatabaseConnection", back_populates="queries")


class DatabaseConnection(Base):
    """
    SECURITY NOTE: connection_string is stored in plaintext. Fine for local/
    resume-demo use. Do not expose this table or this app publicly without
    adding encryption at rest or moving credentials to a secrets manager.
    The connection string you provide should point to a READ-ONLY database
    user -- this app validates queries as defense-in-depth, but the real
    guarantee against writes has to come from DB-level permissions.
    """
    __tablename__ = "database_connections"

    id = Column(String, primary_key=True, default=gen_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=True)  # see note on UploadedFile.user_id
    label = Column(String, nullable=False)
    connection_string = Column(Text, nullable=False)
    dialect = Column(String, nullable=False)
    schema_summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="databases")
    queries = relationship(
        "QueryHistory", back_populates="database", cascade="all, delete-orphan"
    )


class AsyncJob(Base):
    """
    Tracks WHO submitted each async job (Celery task id doubles as this
    row's id). Needed because Celery's result backend alone has no concept
    of ownership -- without this table, anyone who obtained a job_id could
    poll GET /jobs/{job_id} and read someone else's result. The route
    checks AsyncJob.user_id against the requesting user before returning
    anything from the Celery result backend.
    """
    __tablename__ = "async_jobs"

    id = Column(String, primary_key=True)  # same value as the Celery task id
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    source_type = Column(String, nullable=False)  # "csv" or "database"
    source_id = Column(String, nullable=False)  # file_id or db_id
    question = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
