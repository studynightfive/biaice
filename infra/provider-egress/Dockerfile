FROM python:3.12.11-slim-bookworm@sha256:519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --gid 10002 egress \
    && useradd --uid 10002 --gid 10002 --no-create-home --home-dir /nonexistent egress

WORKDIR /opt/biaice-egress
COPY --chown=egress:egress infra/provider-egress/proxy.py ./proxy.py
USER 10002:10002
EXPOSE 8888
CMD ["python", "/opt/biaice-egress/proxy.py"]
