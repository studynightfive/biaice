# Biaice generated contracts

`openapi.generated.json`, the error/event catalogs and `generated-typescript/**`
are generated artifacts. Do not edit them by hand.

From the repository root:

```powershell
python packages/contracts/scripts/generate_contracts.py
python packages/contracts/scripts/generate_contracts.py --check
```

`x-contract-only: true` means the method/path/operationId/owner/permission
contract exists, but the handler deliberately returns RFC 7807 `501
NOT_IMPLEMENTED`. Its field schema remains blocked until the owning member's
jointly reviewed schema PR changes `x-schema-status` from
`STUB_FIELDS_PENDING_OWNER_FREEZE`.
