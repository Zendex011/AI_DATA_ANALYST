"""
Caches /ask and /ask-db responses so an identical question against the same
source doesn't re-run the LLM and re-execute code every time.

Redis is treated as optional infrastructure, not a hard dependency: if it's
unreachable, every function here degrades to "no cache" rather than raising.
A demo running with no Redis at all should work exactly like Phase 3 --
just without the speedup.
"""
from fastapi.encoders import jsonable_encoder
import hashlib
import json
import redis
from app.config import REDIS_URL, REDIS_CACHE_TTL_SECONDS

_redis_client = None


def _get_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(
            REDIS_URL, decode_responses=True, socket_connect_timeout=2
        )
    return _redis_client


def _make_key(source_id: str, question: str) -> str:
    # Normalize whitespace/case so "What is X?" and "what is x?" hit the
    # same cache entry -- questions are rarely typed identically twice.
    normalized = question.strip().lower()
    raw = f"{source_id}:{normalized}"
    return "askcache:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_cached(source_id: str, question: str) -> dict | None:
    try:
        client = _get_client()
        cached = client.get(_make_key(source_id, question))
        return json.loads(cached) if cached else None
    except redis.exceptions.RedisError:
        return None


def set_cached(source_id: str, question: str, response: dict) -> None:
    try:
        client = _get_client()
        client.setex(_make_key(source_id, question), REDIS_CACHE_TTL_SECONDS, jsonable_encoder(response))
    except redis.exceptions.RedisError:
        pass  # caching is a bonus, not a requirement -- never break the request over it