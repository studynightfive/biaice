#!/bin/bash
set -euo pipefail

users_file=/run/biaice-keycloak/test-users.env
if [[ ! -f "$users_file" ]]; then
  echo "Missing generated test-user file. Run scripts/init.ps1 first." >&2
  exit 78
fi

# The generated file is ignored by Git and contains synthetic temporary
# passwords only. Never print it or enable shell tracing around this script.
# Existing files from older Windows initialization may use CRLF; the generated
# Base64URL values never contain CR, so strip line-ending CR before sourcing.
# shellcheck disable=SC1090
source <(sed 's/\r$//' "$users_file")

kcadm=/opt/keycloak/bin/kcadm.sh
synthetic_tenant_id=00000000-0000-4000-8000-000000000001
synthetic_data_domain_id=00000000-0000-4000-8000-000000000002
synthetic_project_id=00000000-0000-4000-8000-000000000101
synthetic_decision_unit_id=00000000-0000-4000-8000-000000000201
"$kcadm" config credentials \
  --server http://keycloak:8080 \
  --realm master \
  --user "$KC_BOOTSTRAP_ADMIN_USERNAME" \
  --password "$KC_BOOTSTRAP_ADMIN_PASSWORD" >/dev/null

"$kcadm" get realms/biaice >/dev/null
"$kcadm" update users/profile -r biaice -f /infra/user-profile.json >/dev/null

# Keycloak 26 places the mandatory subject mapper in the built-in `basic`
# client scope. Realm import handles fresh databases; this PUT also reconciles
# databases that were created from an earlier M0 realm file.
web_client_id=$("$kcadm" get clients -r biaice -q clientId=biaice-web \
  --fields id --format csv --noquotes | tail -n 1)
basic_scope_id=$("$kcadm" get client-scopes -r biaice \
  --fields id,name --format csv --noquotes \
  | sed -n 's/^\([^,]*\),basic$/\1/p' \
  | head -n 1)
test -n "$web_client_id"
test -n "$basic_scope_id"
"$kcadm" update "clients/$web_client_id/default-client-scopes/$basic_scope_id" -r biaice >/dev/null

ensure_user() {
  local username=$1
  local email=$2
  local password=$3
  local roles_csv=$4
  local require_totp=$5
  local user_id
  local password_error
  local required_actions
  local user_payload

  user_id=$("$kcadm" get users -r biaice -q "username=$username" --fields id,username \
    | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
    | head -n 1)

  if [[ -z "$user_id" ]]; then
    "$kcadm" create users -r biaice \
      -s "username=$username" \
      -s "email=$email" \
      -s enabled=true \
      -s emailVerified=true >/dev/null
    user_id=$("$kcadm" get users -r biaice -q "username=$username" --fields id,username \
      | sed -n 's/.*"id"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
      | head -n 1)
  fi

  test -n "$user_id"
  password_error=$(mktemp)
  if ! "$kcadm" set-password -r biaice --userid "$user_id" --new-password "$password" --temporary \
    >/dev/null 2>"$password_error"; then
    # Reapplying the current temporary password is rejected by Keycloak's
    # password-history policy. Treat only that exact response as idempotent;
    # policy failures and transport errors still stop initialization.
    if ! grep -q 'invalidPasswordHistoryMessage' "$password_error"; then
      cat "$password_error" >&2
      rm -f "$password_error"
      return 1
    fi
  fi
  rm -f "$password_error"

  if [[ "$require_totp" == "true" ]]; then
    required_actions='["UPDATE_PASSWORD","CONFIGURE_TOTP"]'
  else
    required_actions='["UPDATE_PASSWORD"]'
  fi

  # Scope is asserted by the API from signed token claims. These deterministic
  # UUIDs refer only to the shared synthetic M0 workspace and are never reused
  # as real tenant or project identifiers. A complete UserRepresentation avoids
  # kcadm's nested --set coercing the attributes map into a string.
  user_payload=$(mktemp)
  cat >"$user_payload" <<JSON
{
  "id": "$user_id",
  "username": "$username",
  "email": "$email",
  "enabled": true,
  "emailVerified": true,
  "firstName": "Synthetic",
  "lastName": "$username",
  "attributes": {
    "tenant_id": ["$synthetic_tenant_id"],
    "data_domain_id": ["$synthetic_data_domain_id"],
    "project_ids": ["$synthetic_project_id"],
    "decision_unit_ids": ["$synthetic_decision_unit_id"]
  },
  "requiredActions": $required_actions
}
JSON
  "$kcadm" update "users/$user_id" -r biaice -f "$user_payload" >/dev/null
  rm -f "$user_payload"

  IFS=',' read -r -a roles <<< "$roles_csv"
  for role in "${roles[@]}"; do
    "$kcadm" add-roles -r biaice --uid "$user_id" --rolename "$role" >/dev/null
  done
}

ensure_user m1-lead       m1-lead@biaice.test       "$BIAICE_M1_PASSWORD" "SYSTEM_ADMIN,GOVERNANCE_ADMIN" true
ensure_user m2-projects   m2-projects@biaice.test   "$BIAICE_M2_PASSWORD" "PROJECT_MANAGER,RULE_EDITOR" false
ensure_user m3-documents  m3-documents@biaice.test  "$BIAICE_M3_PASSWORD" "DOCUMENT_STEWARD" false
ensure_user m4-commercial m4-commercial@biaice.test "$BIAICE_M4_PASSWORD" "COMMERCIAL_ANALYST" true
ensure_user m5-privacy-ai m5-privacy-ai@biaice.test "$BIAICE_M5_PASSWORD" "TENANT_AI_ADMIN,PRIVACY_OFFICER" true
ensure_user m6-simulation m6-simulation@biaice.test "$BIAICE_M6_PASSWORD" "SIMULATION_ANALYST" false
ensure_user m7-approvals  m7-approvals@biaice.test  "$BIAICE_M7_PASSWORD" "APPROVER,REPORT_MANAGER" true

echo "Seven synthetic test accounts are present; all passwords are temporary."
