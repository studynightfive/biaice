# The AppRole alias must be attached to an identity entity whose immutable
# tenant_id metadata is set by the dual-control initialization ceremony.
# Omitting read/list is an intentional deny: this identity can never retrieve
# plaintext or enumerate another tenant (or even its own tenant) credentials.
path "secret/data/tenants/{{identity.entity.metadata.tenant_id}}/providers/+/purposes/+" {
  capabilities = ["create", "update", "patch"]
}

path "secret/delete/tenants/{{identity.entity.metadata.tenant_id}}/providers/+/purposes/+" {
  capabilities = ["update"]
}

path "secret/undelete/tenants/{{identity.entity.metadata.tenant_id}}/providers/+/purposes/+" {
  capabilities = ["update"]
}

path "secret/destroy/tenants/{{identity.entity.metadata.tenant_id}}/providers/+/purposes/+" {
  capabilities = ["update"]
}

path "secret/metadata/tenants/{{identity.entity.metadata.tenant_id}}/providers/+/purposes/+" {
  capabilities = ["delete"]
}

path "sys/capabilities-self" {
  capabilities = ["update"]
}
