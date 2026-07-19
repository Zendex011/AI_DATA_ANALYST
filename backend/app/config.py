import os
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
MAX_CODE_EXEC_SECONDS = int(os.getenv("MAX_CODE_EXEC_SECONDS", "10"))
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")

# Hard ceiling on Gemini's response length. Without this, a rambling
# explanation in the interpret step has no upper bound and quietly costs
# real money. Code generation needs less room than the final explanation.
GEMINI_MAX_OUTPUT_TOKENS_CODE = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS_CODE", "1024"))
GEMINI_MAX_OUTPUT_TOKENS_TEXT = int(os.getenv("GEMINI_MAX_OUTPUT_TOKENS_TEXT", "1024"))

# Defaults to a local SQLite file so the app runs with zero setup.
# Point this at Postgres in .env for anything beyond local testing:
#   postgresql://user:password@localhost:5432/ai_data_analyst
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app_data.db")

# Caching is entirely optional -- if Redis isn't running, cache.py catches
# the connection error and treats it as a cache miss rather than crashing.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_CACHE_TTL_SECONDS = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "3600"))

# "docker" = real sandbox (no network, read-only fs, memory/cpu limits,
# ephemeral container per run) -- requires Docker running and the sandbox
# image built (see docker/SANDBOX_SETUP.md).
# "subprocess" = Phase 1-4 behavior (timeout only, no real isolation) --
# zero setup, useful if Docker isn't available yet, but NOT safe for
# untrusted/public use. Default is "docker" on purpose: the safe path
# should be the one you get without having to remember to opt in.
SANDBOX_MODE = os.getenv("SANDBOX_MODE", "docker")
SANDBOX_IMAGE_NAME = os.getenv("SANDBOX_IMAGE_NAME", "ai-data-analyst-sandbox")
SANDBOX_MEM_LIMIT = os.getenv("SANDBOX_MEM_LIMIT", "256m")
SANDBOX_CPU_NANOS = int(float(os.getenv("SANDBOX_CPU_LIMIT", "0.5")) * 1_000_000_000)

# --- Auth ---
# CHANGE THIS in any real deployment. The fallback exists so the app still
# runs with zero setup for local dev, but a default secret means anyone who
# reads this source can forge tokens for your instance.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

if JWT_SECRET_KEY == "dev-only-insecure-secret-change-me":
    print(
        "WARNING: JWT_SECRET_KEY is using the insecure default. Set a real "
        "secret in .env before deploying this anywhere reachable by others."
    )

# --- Celery (async jobs) ---
# Reuses the same Redis instance as the Phase 4 cache but a different DB
# index (1 instead of 0), so task/result keys never collide with cache keys.
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

if not GEMINI_API_KEY:
    # Fail loud, not silent. A missing key should not surface as a
    # confusing downstream LangChain error.
    print("WARNING: GEMINI_API_KEY is not set. Set it in your .env file.")