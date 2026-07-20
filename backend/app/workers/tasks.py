"""
Celery tasks run in a separate worker process from the FastAPI app, so
they can't use FastAPI's request-scoped get_db() dependency -- each task
opens and closes its own SQLAlchemy session directly.
"""

from app.workers.celery_app import celery_app
from app.db.database import SessionLocal
from app.services.ask_service import run_csv_ask, run_db_ask


@celery_app.task(name="run_csv_ask_task")
def run_csv_ask_task(
    file_id: str, question: str, include_chart: bool, gemini_api_key: str | None = None
) -> dict:
    db = SessionLocal()
    try:
        return run_csv_ask(db, file_id, question, include_chart, gemini_api_key)
    finally:
        db.close()


@celery_app.task(name="run_db_ask_task")
def run_db_ask_task(
    db_id: str, question: str, include_chart: bool, gemini_api_key: str | None = None
) -> dict:
    db = SessionLocal()
    try:
        return run_db_ask(db, db_id, question, include_chart, gemini_api_key)
    finally:
        db.close()
