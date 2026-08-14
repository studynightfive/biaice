#!/bin/sh
set -eu

test -f "${RESTIC_PASSWORD_FILE:?RESTIC_PASSWORD_FILE is required}" || {
  echo "Restic password file is missing." >&2
  exit 78
}
test -s "$RESTIC_PASSWORD_FILE" || {
  echo "Restic password file is empty." >&2
  exit 78
}

action=${BACKUP_ACTION:-}
case "$action" in
  backup)
    test -s /snapshot/staging/manifest.json
    test -s /snapshot/staging/biaice.dump
    test -s /snapshot/staging/keycloak.dump
    if ! restic snapshots >/dev/null 2>&1; then
      restic init
    fi
    restic backup /snapshot \
      --tag biaice \
      --tag encrypted \
      --host biaice-compose
    restic check
    ;;
  verify)
    snapshot=${RESTORE_SNAPSHOT:-}
    echo "$snapshot" | grep -Eq '^[0-9a-f]{8,64}$' || {
      echo "An exact hexadecimal snapshot ID is required; latest is forbidden." >&2
      exit 64
    }
    restic snapshots "$snapshot"
    restic check
    ;;
  restore)
    snapshot=${RESTORE_SNAPSHOT:-}
    echo "$snapshot" | grep -Eq '^[0-9a-f]{8,64}$' || {
      echo "An exact hexadecimal snapshot ID is required; latest is forbidden." >&2
      exit 64
    }
    # /restore is a dedicated named staging volume, never a host or data root.
    find /restore -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
    restic restore "$snapshot" --target /restore
    test -s /restore/snapshot/staging/manifest.json
    test -s /restore/snapshot/staging/biaice.dump
    test -s /restore/snapshot/staging/keycloak.dump
    ;;
  *)
    echo "Unsupported BACKUP_ACTION." >&2
    exit 64
    ;;
esac
