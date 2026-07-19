from celery import Celery
from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

celery_app = Celery(
    "ai_data_analyst",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # A generous hard cap so a runaway task can't occupy a worker forever.
    # This is independent of MAX_CODE_EXEC_SECONDS -- that bounds the
    # sandboxed code itself; this bounds the whole task (LLM calls + retry
    # + chart generation combined).
    task_time_limit=120,
)