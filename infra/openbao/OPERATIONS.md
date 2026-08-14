# OpenBao secure-mode baseline

This Compose service always uses integrated Raft storage. It never uses
`server -dev`, a fixed root token, auto-unseal output, or an environment-held
unseal/recovery share.

Before either `BYOK_SECRET_GATE` or `REAL_DATA_MODE` may pass, two operators
must perform and record a one-time ceremony:

1. initialize with three shares and threshold two, writing the JSON output
   directly to approved encrypted removable/off-host storage (never stdout,
   this repository, Compose, `.env`, images, logs, or ordinary backups);
2. distribute all three shares to three distinct custodians and test 2-of-3
   seal/unseal and lost-share recovery;
3. enable KV v2 and the file audit device under `/openbao/logs`;
4. install the repository policies, create tenant-scoped short-TTL AppRoles,
   and make egress use only single-use response wrapping;
5. revoke the initial root token, or seal it under documented offline
   dual-control custody; and
6. write machine-verifiable evidence and its hash for the Gate assessor.

`provider-egress-gateway` separately requires a current Gate evidence file and
matching allowlist hash. A healthy-but-sealed OpenBao server never counts as a
passing Gate. Restore must recover this Raft state before identity or business
data and must stop if the original key material cannot be recovered.

OpenBao 2.3 no longer supports `mlock`. Before any secure-profile ceremony,
the host must disable swap or use platform-managed encrypted swap and record
that machine evidence in both security Gates.
