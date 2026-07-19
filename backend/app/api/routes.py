import csv
import io
import json
import os
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from app.config import UPLOAD_DIR
from app.db.database import get_db
from app.db.models import UploadedFile, QueryHistory, DatabaseConnection, User, AsyncJob
from app.models.schemas import (
    AskRequest,
    AskResponse,
    UploadResponse,
    FileListItem,
    HistoryItem,
    ConnectDBRequest,
    ConnectDBResponse,
    AskDBRequest,
    AskDBResponse,
    AskAsyncResponse,
    JobStatusResponse,
    DatabaseListItem,
)
from app.core.db_schema import reflect_schema
from app.services.ask_service import run_csv_ask, run_db_ask
from app.workers.tasks import run_csv_ask_task, run_db_ask_task
from app.auth.dependencies import get_current_user
from sqlalchemy.exc import SQLAlchemyError


def _find_duplicate_headers(content: bytes) -> list[str]:
    """
    Reads only the first line of the raw file and returns any column names
    that appear more than once. Must run BEFORE pd.read_csv, since pandas
    auto-renames duplicates on the way in (see comment at call site).
    """
    try:
        first_line = content.split(b"\n", 1)[0].decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return []  # encoding error already caught earlier by pd.read_csv

    header = next(csv.reader([first_line]))
    seen = set()
    duplicates = []
    for col in header:
        if col in seen and col not in duplicates:
            duplicates.append(col)
        seen.add(col)
    return duplicates


router = APIRouter()
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(400, "Only CSV files are supported in Phase 1")

    content = await file.read()

    if len(content) == 0:
        raise HTTPException(400, "Uploaded file is empty")

    try:
        df = pd.read_csv(io.BytesIO(content))
    except pd.errors.EmptyDataError:
        raise HTTPException(400, "Uploaded file has no columns to parse")
    except pd.errors.ParserError as e:
        raise HTTPException(400, f"Invalid CSV file: could not parse rows ({e})")
    except UnicodeDecodeError:
        raise HTTPException(
            400, "Invalid CSV file: not a valid text/CSV encoding (is this really a CSV?)"
        )

    if df.shape[0] == 0:
        raise HTTPException(400, "CSV contains no data rows")

    duplicate_cols = _find_duplicate_headers(content)
    if duplicate_cols:
        raise HTTPException(
            400,
            f"CSV has duplicate column names: {duplicate_cols}. "
            "Rename or remove duplicates before uploading.",
        )

    file_id = str(uuid.uuid4())
    path = os.path.join(UPLOAD_DIR, f"{file_id}.csv")
    with open(path, "wb") as f:
        f.write(content)

    dtypes = {col: str(dtype) for col, dtype in df.dtypes.items()}

    db_file = UploadedFile(
        id=file_id,
        user_id=current_user.id,
        filename=file.filename,
        path=path,
        rows=df.shape[0],
        columns=",".join(df.columns.tolist()),
        dtypes=json.dumps(dtypes),
    )
    db.add(db_file)
    db.commit()

    return UploadResponse(
        file_id=file_id,
        filename=file.filename,
        rows=df.shape[0],
        columns=df.columns.tolist(),
    )


@router.get("/files", response_model=list[FileListItem])
def list_files(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    files = (
        db.query(UploadedFile)
        .filter(UploadedFile.user_id == current_user.id)
        .order_by(UploadedFile.uploaded_at.desc())
        .all()
    )
    return [
        FileListItem(
            file_id=f.id,
            filename=f.filename,
            rows=f.rows,
            columns=f.columns_list(),
            uploaded_at=f.uploaded_at,
        )
        for f in files
    ]


def _get_owned_file(db: Session, file_id: str, current_user: User) -> UploadedFile:
    """
    404s (not 403) whether the file doesn't exist OR belongs to someone
    else -- deliberately not distinguishing the two, so a user can't use
    the error code itself to discover which file_ids exist for other people.
    """
    db_file = (
        db.query(UploadedFile)
        .filter(UploadedFile.id == file_id, UploadedFile.user_id == current_user.id)
        .first()
    )
    if not db_file:
        raise HTTPException(404, "File not found")
    return db_file


def _get_owned_db(db: Session, db_id: str, current_user: User) -> DatabaseConnection:
    db_conn = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.id == db_id, DatabaseConnection.user_id == current_user.id)
        .first()
    )
    if not db_conn:
        raise HTTPException(404, "Database connection not found")
    return db_conn


@router.get("/history/{file_id}", response_model=list[HistoryItem])
def get_history(
    file_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_file(db, file_id, current_user)  # 404s if missing or not yours

    history = (
        db.query(QueryHistory)
        .filter(QueryHistory.file_id == file_id)
        .order_by(QueryHistory.created_at.desc())
        .all()
    )
    return [HistoryItem.model_validate(h) for h in history]


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    req: AskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_file(db, req.file_id, current_user)
    try:
        response_data = run_csv_ask(db, req.file_id, req.question, req.include_chart)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return AskResponse(**response_data)


@router.post("/ask-async", response_model=AskAsyncResponse)
def ask_question_async(
    req: AskRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """
    Same question as /ask, but returns immediately with a job_id instead of
    blocking on the LLM calls + code execution. Poll GET /jobs/{job_id} for
    the result. Prefer this over /ask for anything you expect to be slow
    (large datasets, chart generation, or just being kind to your own
    request timeout settings).
    """
    _get_owned_file(db, req.file_id, current_user)

    task = run_csv_ask_task.delay(req.file_id, req.question, req.include_chart)

    job = AsyncJob(
        id=task.id,
        user_id=current_user.id,
        source_type="csv",
        source_id=req.file_id,
        question=req.question,
    )
    db.add(job)
    db.commit()

    return AskAsyncResponse(job_id=task.id)


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
def get_job_status(
    job_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    job = db.query(AsyncJob).filter(AsyncJob.id == job_id).first()
    if not job or job.user_id != current_user.id:
        # Same not-found-vs-not-yours non-disclosure as _get_owned_file/_get_owned_db --
        # a job_id you don't own should look identical to one that never existed.
        raise HTTPException(404, "Job not found")

    from celery.result import AsyncResult
    from app.workers.celery_app import celery_app

    result = AsyncResult(job_id, app=celery_app)

    if result.state == "PENDING":
        return JobStatusResponse(job_id=job_id, status="pending")
    if result.state in ("STARTED", "RETRY"):
        return JobStatusResponse(job_id=job_id, status="running")
    if result.state == "SUCCESS":
        return JobStatusResponse(job_id=job_id, status="done", result=result.result)
    if result.state == "FAILURE":
        return JobStatusResponse(
            job_id=job_id, status="failed", result={"error": str(result.info)}
        )
    return JobStatusResponse(job_id=job_id, status=result.state.lower())


@router.get("/databases", response_model=list[DatabaseListItem])
def list_databases(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    connections = (
        db.query(DatabaseConnection)
        .filter(DatabaseConnection.user_id == current_user.id)
        .order_by(DatabaseConnection.created_at.desc())
        .all()
    )
    return [
        DatabaseListItem(
            db_id=c.id,
            label=c.label,
            dialect=c.dialect,
            schema_summary=c.schema_summary,
            created_at=c.created_at,
        )
        for c in connections
    ]


@router.post("/connect-db", response_model=ConnectDBResponse)
def connect_database(
    req: ConnectDBRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Registers an external database connection. Reads the schema once here
    so /ask-db never has to re-connect and re-inspect on every question.

    IMPORTANT: this endpoint does not and cannot verify that the connection
    string points to a read-only user -- that is your responsibility to set
    up on the database side. This app validates generated SQL as
    defense-in-depth (see sql_validator.py), not as a substitute for it.
    """
    try:
        schema_summary, dialect = reflect_schema(req.connection_string)
    except SQLAlchemyError as e:
        raise HTTPException(400, f"Could not connect to database: {e}")
    except Exception as e:
        raise HTTPException(400, f"Could not connect to database: {type(e).__name__}: {e}")

    if not schema_summary:
        raise HTTPException(400, "Connected successfully but found no tables")

    db_id = str(uuid.uuid4())
    db_conn = DatabaseConnection(
        id=db_id,
        user_id=current_user.id,
        label=req.label,
        connection_string=req.connection_string,
        dialect=dialect,
        schema_summary=schema_summary,
    )
    db.add(db_conn)
    db.commit()

    return ConnectDBResponse(
        db_id=db_id,
        label=req.label,
        dialect=dialect,
        schema_summary=schema_summary,
    )


@router.post("/ask-db", response_model=AskDBResponse)
def ask_database(
    req: AskDBRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_db(db, req.db_id, current_user)
    try:
        response_data = run_db_ask(db, req.db_id, req.question, req.include_chart)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return AskDBResponse(**response_data)


@router.post("/ask-db-async", response_model=AskAsyncResponse)
def ask_database_async(
    req: AskDBRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_db(db, req.db_id, current_user)

    task = run_db_ask_task.delay(req.db_id, req.question, req.include_chart)

    job = AsyncJob(
        id=task.id,
        user_id=current_user.id,
        source_type="database",
        source_id=req.db_id,
        question=req.question,
    )
    db.add(job)
    db.commit()

    return AskAsyncResponse(job_id=task.id)


@router.get("/history-db/{db_id}", response_model=list[HistoryItem])
def get_db_history(
    db_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _get_owned_db(db, db_id, current_user)

    history = (
        db.query(QueryHistory)
        .filter(QueryHistory.db_id == db_id)
        .order_by(QueryHistory.created_at.desc())
        .all()
    )
    return [HistoryItem.model_validate(h) for h in history]