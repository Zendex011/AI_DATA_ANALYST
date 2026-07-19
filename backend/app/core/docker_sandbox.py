"""
Runs a Python script inside a locked-down, ephemeral Docker container.
Shared by code_executor.py (pandas) and chart_generator.py (matplotlib) --
this module only knows how to run a script safely; it doesn't know
anything about pandas, matplotlib, or error-marker parsing.

Isolation provided, compared to the Phase 1-4 subprocess approach:
  - network_disabled=True       -- no network access from inside the code
  - read_only=True              -- root filesystem is read-only; only the
                                    explicitly mounted paths are writable
  - mem_limit / nano_cpus       -- real cgroup-enforced resource limits,
                                    not just "hope the timeout catches it"
  - user="1000:1000"            -- runs as a non-root user
  - remove(force=True)          -- container is destroyed after every run,
                                    nothing persists between requests

Requires:
  - Docker (or Docker Desktop) running and reachable from this machine
  - The sandbox image built once:
      docker build -t ai-data-analyst-sandbox -f docker/sandbox.Dockerfile docker/
    (see docker/SANDBOX_SETUP.md)

NOT YET LIVE-TESTED against a real Docker daemon at the time this was
written -- there was no Docker available in the environment this was built
in. The logic here follows docker-py's documented API precisely and has
been checked with mocked Docker responses, but you should run
docker/test_sandbox.py on your own machine before relying on this.
"""

import docker
from docker.errors import ImageNotFound, APIError
import requests.exceptions

from app.config import (
    MAX_CODE_EXEC_SECONDS,
    SANDBOX_IMAGE_NAME,
    SANDBOX_MEM_LIMIT,
    SANDBOX_CPU_NANOS,
)


class SandboxExecutionError(Exception):
    """
    error_type values you should specifically handle at the call site:
      - "SandboxImageNotFound" -- image hasn't been built yet
      - "DockerUnavailable"    -- Docker daemon isn't running/reachable
      - "TimeoutError"         -- container exceeded MAX_CODE_EXEC_SECONDS
      - "ExecutionError"       -- the script itself exited non-zero
        (error_message is the raw combined stdout+stderr in this case --
        callers that expect a JSON error marker should parse it themselves)
    """

    def __init__(self, error_type: str, error_message: str):
        self.error_type = error_type
        self.error_message = error_message
        super().__init__(f"{error_type}: {error_message}")


_docker_client = None


def _get_client():
    global _docker_client
    if _docker_client is None:
        try:
            _docker_client = docker.from_env()
        except Exception as e:
            raise SandboxExecutionError(
                "DockerUnavailable",
                f"Could not connect to Docker: {e}. Is Docker Desktop/daemon running?",
            )
    return _docker_client


def run_in_sandbox(volumes: dict, extra_env: dict | None = None) -> str:
    """
    Runs `python /sandbox/script.py` inside the sandbox image.
    volumes: already in docker-py's format, e.g.
      {"/host/path/script.py": {"bind": "/sandbox/script.py", "mode": "ro"}}
    Returns combined stdout+stderr as text on success (exit code 0).
    Raises SandboxExecutionError for every other outcome -- never lets a
    raw docker-py exception escape to the caller.
    """
    client = _get_client()

    try:
        container = client.containers.run(
            image=SANDBOX_IMAGE_NAME,
            command=["python", "/sandbox/script.py"],
            volumes=volumes,
            tmpfs={"/tmp": "size=64m"},  # writable scratch space even with read_only=True
            environment={"MPLCONFIGDIR": "/tmp", **(extra_env or {})},
            network_disabled=True,
            mem_limit=SANDBOX_MEM_LIMIT,
            nano_cpus=SANDBOX_CPU_NANOS,
            read_only=True,
            user="1000:1000",
            detach=True,
        )
    except ImageNotFound:
        raise SandboxExecutionError(
            "SandboxImageNotFound",
            f"Docker image '{SANDBOX_IMAGE_NAME}' not found. Build it first: "
            f"docker build -t {SANDBOX_IMAGE_NAME} -f docker/sandbox.Dockerfile docker/",
        )
    except APIError as e:
        raise SandboxExecutionError(
            "DockerUnavailable", f"Could not start sandbox container: {e}"
        )

    try:
        try:
            # `timeout` here bounds the client's wait on the Docker Engine
            # API, not the container's execution directly -- if it fires,
            # the container is still running and must be killed explicitly
            # below. This is the documented pattern for enforcing a
            # execution timeout with docker-py.
            result = container.wait(timeout=MAX_CODE_EXEC_SECONDS)
        except requests.exceptions.ReadTimeout:
            container.kill()
            raise SandboxExecutionError(
                "TimeoutError", f"Execution exceeded {MAX_CODE_EXEC_SECONDS}s"
            )

        logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="replace")
        exit_code = result.get("StatusCode", 1)

        if exit_code != 0:
            raise SandboxExecutionError(
                "ExecutionError", logs.strip() or "Sandbox exited non-zero with no output"
            )

        return logs
    finally:
        try:
            container.remove(force=True)
        except Exception:
            pass  # ephemeral either way -- don't fail the request over cleanup