"""Per-user Gemini API key: encryption, endpoints, and that it actually reaches get_llm()."""

from unittest.mock import patch
from app.core.crypto import encrypt_secret, decrypt_secret


def test_encrypt_decrypt_roundtrip():
    plaintext = "AIzaSy-fake-example-key-1234567890"
    ciphertext = encrypt_secret(plaintext)
    assert ciphertext != plaintext
    assert decrypt_secret(ciphertext) == plaintext


def test_api_key_status_defaults_to_false(client, auth_headers):
    resp = client.get("/auth/api-key", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["has_custom_key"] is False


def test_set_and_check_api_key(client, auth_headers):
    resp = client.put(
        "/auth/api-key", json={"gemini_api_key": "AIzaSy-my-own-key"}, headers=auth_headers
    )
    assert resp.status_code == 200
    assert resp.json()["has_custom_key"] is True

    resp = client.get("/auth/api-key", headers=auth_headers)
    assert resp.json()["has_custom_key"] is True


def test_empty_api_key_rejected(client, auth_headers):
    resp = client.put("/auth/api-key", json={"gemini_api_key": "   "}, headers=auth_headers)
    assert resp.status_code == 400


def test_delete_api_key(client, auth_headers):
    client.put("/auth/api-key", json={"gemini_api_key": "AIzaSy-key"}, headers=auth_headers)
    resp = client.delete("/auth/api-key", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["has_custom_key"] is False

    resp = client.get("/auth/api-key", headers=auth_headers)
    assert resp.json()["has_custom_key"] is False


def test_api_key_never_returned_in_plaintext(client, auth_headers):
    resp = client.put(
        "/auth/api-key", json={"gemini_api_key": "AIzaSy-should-never-appear"}, headers=auth_headers
    )
    assert "AIzaSy-should-never-appear" not in resp.text

    resp = client.get("/auth/api-key", headers=auth_headers)
    assert "AIzaSy-should-never-appear" not in resp.text


def test_users_own_key_actually_reaches_get_llm(client, auth_headers):
    """
    The point of the whole feature: confirms the decrypted key set via
    PUT /auth/api-key is the exact value passed as api_key= to get_llm()
    during a real /ask call -- not just that the endpoints work in isolation.
    """
    client.put("/auth/api-key", json={"gemini_api_key": "AIzaSy-user-specific-key"}, headers=auth_headers)

    csv_content = b"x,y\n1,2\n3,4\n"
    resp = client.post(
        "/upload", files={"file": ("t.csv", csv_content, "text/csv")}, headers=auth_headers
    )
    file_id = resp.json()["file_id"]

    captured_keys = []

    def spy_get_llm(temperature=0, max_output_tokens=None, api_key=None):
        captured_keys.append(api_key)
        from tests.conftest import FakeLLM
        return FakeLLM()

    # Patched where `get_llm` is actually bound (orchestrator.py did
    # `from app.core.llm import get_llm` at import time, which created its
    # own local reference) -- patching app.core.llm.get_llm again here
    # wouldn't reach that already-bound name.
    with patch("app.agents.orchestrator.get_llm", side_effect=spy_get_llm):
        resp = client.post(
            "/ask", json={"file_id": file_id, "question": "count rows"}, headers=auth_headers
        )
        assert resp.status_code == 200

    assert len(captured_keys) > 0, "get_llm was never called"
    assert all(k == "AIzaSy-user-specific-key" for k in captured_keys), (
        f"Expected every get_llm call to receive the user's own key, got: {captured_keys}"
    )


def test_user_without_own_key_gets_none(client, auth_headers):
    """A user who never set their own key should pass api_key=None through
    to get_llm(), which is what makes it fall back to the shared GEMINI_API_KEY."""
    csv_content = b"x,y\n1,2\n3,4\n"
    resp = client.post(
        "/upload", files={"file": ("t2.csv", csv_content, "text/csv")}, headers=auth_headers
    )
    file_id = resp.json()["file_id"]

    captured_keys = []

    def spy_get_llm(temperature=0, max_output_tokens=None, api_key=None):
        captured_keys.append(api_key)
        from tests.conftest import FakeLLM
        return FakeLLM()

    with patch("app.agents.orchestrator.get_llm", side_effect=spy_get_llm):
        resp = client.post(
            "/ask", json={"file_id": file_id, "question": "count rows"}, headers=auth_headers
        )
        assert resp.status_code == 200

    assert len(captured_keys) > 0
    assert all(k is None for k in captured_keys)
