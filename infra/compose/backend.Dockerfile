FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7 AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/opt/biaice/app/src \
    PATH=/opt/biaice/.local/bin:${PATH}

RUN groupadd --gid 10001 biaice \
    && useradd --uid 10001 --gid 10001 --create-home --home-dir /opt/biaice biaice

WORKDIR /opt/biaice/app
COPY --chown=biaice:biaice apps/backend/requirements.lock ./
RUN python -m pip install --no-cache-dir --require-hashes --requirement requirements.lock

COPY --chown=biaice:biaice apps/backend/alembic.ini ./
COPY --chown=biaice:biaice apps/backend/src/ ./src/
COPY --chown=biaice:biaice apps/backend/migrations/ ./migrations/

USER 10001:10001
EXPOSE 8000

CMD ["python", "-m", "uvicorn", "biaice.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-server-header"]
