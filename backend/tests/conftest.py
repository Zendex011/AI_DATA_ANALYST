"""
Shared fixtures for the test suite. Runs entirely offline:
  - Gemini is mocked (no real API key or network call needed)
  - SANDBOX_MODE is forced to "subprocess" (no Docker daemon needed in CI)
  - A fresh SQLite file per test session (no Postgres needed in CI)
"""

import os
import tempfile

os.environ["GEMINI_API_KEY"] = "test-dummy-key"
os.environ["SANDBOX_MODE"] = "subprocess"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-ci-only"

_db_fd, _db_path = tempfile.mkstemp(suffix=".db")
os.environ["DATABASE_URL"] = f"sqlite:///{_db_path}"

_upload_dir = tempfile.mkdtemp()
os.environ["UPLOAD_DIR"] = _upload_dir

import pytest
from fastapi.testclient import TestClient


class FakeResponse:
    def __init__(self, content):
        self.content = content
        self.response_metadata = {"finish_reason": "STOP"}


class FakeLLM:
    """
    Deterministic stand-in for Gemini. Branches on distinctive phrases from
    each prompt so different test questions get sensible fake answers
    without needing a real model call.
    """

    def invoke(self, prompt):
        if "Write pandas code" in prompt or "Fix the code" in prompt:
            return FakeResponse("print(df.iloc[:, 0].count())")
        if "Write a SQL query" in prompt or "Fix the query" in prompt:
            return FakeResponse("SELECT COUNT(*) as total FROM test_table")
        if "Would a chart" in prompt:
            return FakeResponse("NO")
        return FakeResponse("This is a test answer.")


@pytest.fixture(scope="session", autouse=True)
def patch_llm():
    import app.core.llm as llm_module
    llm_module.get_llm = lambda temperature=0, max_output_tokens=None, api_key=None: FakeLLM()
    yield


@pytest.fixture()
def client():
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth_headers(client):
    """Signs up a fresh user and returns ready-to-use auth headers."""
    import uuid
    email = f"test-{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/auth/signup", json={"email": email, "password": "testpass123"})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
