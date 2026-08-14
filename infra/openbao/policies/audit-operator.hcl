path "sys/audit" {
  capabilities = ["read"]
}

path "sys/audit/*" {
  capabilities = ["create", "update"]
}

path "sys/storage/raft/snapshot" {
  capabilities = ["read"]
}

path "sys/health" {
  capabilities = ["read"]
}
