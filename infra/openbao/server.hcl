ui = false
disable_clustering = false

storage "raft" {
  path    = "/openbao/file"
  node_id = "biaice-openbao-1"
}

listener "tcp" {
  address         = "0.0.0.0:8200"
  cluster_address = "0.0.0.0:8201"
  tls_disable     = 1
}

api_addr     = "http://openbao:8200"
cluster_addr = "http://openbao:8201"

telemetry {
  disable_hostname          = true
  prometheus_retention_time = "30s"
}

# This is an integrated-storage server, never a dev server. Initialization,
# 2-of-3 share distribution, unseal and initial-root revocation are manual,
# dual-control ceremonies. Tokens and shares are never accepted through env.
