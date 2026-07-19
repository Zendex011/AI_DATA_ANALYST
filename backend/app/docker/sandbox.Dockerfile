# Minimal image for executing LLM-generated pandas/matplotlib code.
# Deliberately small surface area -- no compilers, no shell utilities
# beyond what Python needs, no unnecessary packages.

FROM python:3.12-slim

RUN pip install --no-cache-dir \
    pandas==2.2.2 \
    matplotlib==3.9.2

# Non-root user -- matches the user="1000:1000" the app runs the container
# with in docker_sandbox.py. If you change the UID here, update that too.
RUN useradd -m -u 1000 sandboxuser

WORKDIR /sandbox
USER sandboxuser
