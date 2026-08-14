#!/bin/sh
set -eu

phase=${1:-}
snapshot=${RESTORE_SNAPSHOT:-}
expected="RESTORE BIAICE ${snapshot}"
test -n "$snapshot" || { echo "RESTORE_SNAPSHOT is required." >&2; exit 64; }
test "${RESTORE_CONFIRMATION:-}" = "$expected" || {
  echo "Exact destructive restore confirmation is missing." >&2
  exit 64
}
test -s /restore/snapshot/staging/manifest.json || {
  echo "Restore manifest is missing." >&2
  exit 78
}

replace_tree() {
  source_path=$1
  target_path=$2
  case "$source_path:$target_path" in
    /restore/snapshot/*:/target/*) ;;
    *) echo "Unsafe restore path." >&2; exit 70 ;;
  esac
  test -d "$source_path"
  test -d "$target_path"
  find "$target_path" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
  cp -a "$source_path"/. "$target_path"/
}

case "$phase" in
  crypto)
    # Required first: original OpenBao material and original Caddy local CA.
    replace_tree /restore/snapshot/openbao-data /target/openbao-data
    replace_tree /restore/snapshot/openbao-audit /target/openbao-audit
    replace_tree /restore/snapshot/caddy-data /target/caddy-data
    ;;
  identity)
    # Run only after OpenBao is unsealed. Restore Keycloak ancillary state and
    # logical dumps first; the wrapper restores Keycloak DB before business DB.
    replace_tree /restore/snapshot/keycloak-data /target/keycloak-data
    replace_tree /restore/snapshot/staging /target/staging
    ;;
  objects)
    # Run only after Keycloak and business logical databases have restored.
    replace_tree /restore/snapshot/minio /target/minio
    replace_tree /restore/snapshot/audit-anchors /target/audit-anchors
    ;;
  *)
    echo "Restore phase must be crypto, identity or objects." >&2
    exit 64
    ;;
esac
