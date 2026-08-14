#!/bin/sh
set -eu

mc alias set local http://minio:9000 "$MINIO_ROOT_USER" "$MINIO_ROOT_PASSWORD" >/dev/null

for bucket in quarantine source derived reports audit-anchors; do
  mc mb --ignore-existing "local/${bucket}" >/dev/null
  mc anonymous set none "local/${bucket}" >/dev/null
  mc version enable "local/${bucket}" >/dev/null
done

echo "MinIO synthetic baseline buckets are ready; anonymous access is disabled."
