# Docker Sandbox Setup (Phase 5)

## Why this exists

Phases 1-4 ran LLM-generated code in a plain subprocess with only a
timeout. That protects against infinite loops, but not against network
access, filesystem access outside the CSV, or memory exhaustion. This
phase replaces that with a real sandbox: each execution runs in a fresh,
disposable Docker container with no network, a read-only filesystem
(except the specific mounted files), and memory/CPU limits.

## Setup

1. Install Docker Desktop (Windows/Mac) or Docker Engine (Linux), and make
   sure it's actually running before you start the app.

2. Build the sandbox image once, from the project root:
   ```bash
   docker build -t ai-data-analyst-sandbox -f docker/sandbox.Dockerfile docker/
   ```
   Re-run this only if you change `docker/sandbox.Dockerfile` (e.g. adding
   a package the generated code needs).

3. In `backend/.env`, either leave `SANDBOX_MODE` unset (defaults to
   `docker`) or set it explicitly:
   ```
   SANDBOX_MODE=docker
   ```

4. **Verify it actually works before trusting it** — run:
   ```bash
   python docker/test_sandbox.py
   ```
   This checks five things: basic execution, structured error handling,
   that network access is genuinely blocked, that the filesystem is
   genuinely read-only outside the mounted CSV, and that chart generation
   produces a valid PNG. If any of the security checks (network/filesystem)
   fail, do not run this in front of anyone until you've found out why —
   it means the isolation isn't actually applying.

## Falling back to subprocess mode

If Docker isn't available to you right now (e.g. you're on a machine
where you can't install it), set:
```
SANDBOX_MODE=subprocess
```
This restores the Phase 1-4 behavior. It works with zero setup, but it is
**not** safe for untrusted or public use — there's no network restriction,
filesystem jail, or memory limit, only a timeout. Treat this as a
temporary local-dev convenience, not a production setting.

## Known limitations, even in docker mode

- The Docker daemon itself must be trusted — if someone can reach the
  Docker socket, container isolation doesn't help. This is standard for
  any Docker-based sandboxing and isn't specific to this app.
- Resource limits (`SANDBOX_MEM_LIMIT`, `SANDBOX_CPU_LIMIT` in `.env`)
  are enforced by cgroups, which is real enforcement — but a
  sufficiently exotic escape technique targeting the container runtime
  itself is out of scope for this project. That's an acceptable line to
  draw for a portfolio project; a real production system handling
  genuinely adversarial input would look at gVisor or Firecracker instead
  of plain Docker.
- This was built and logic-tested with a **mocked** Docker client — there
  was no Docker daemon available in the environment it was written in.
  Run `docker/test_sandbox.py` yourself before relying on it; don't take
  "the code looks right" as equivalent to "it's been verified."