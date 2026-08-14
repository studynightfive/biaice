# The egress process receives a response-wrapping token that is single use and
# short TTL. Its standing identity cannot enumerate or directly read secrets.
path "sys/wrapping/unwrap" {
  capabilities = ["update"]
}

path "auth/token/lookup-self" {
  capabilities = ["read"]
}

path "secret/*" {
  capabilities = ["deny"]
}
