[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][ValidatePattern('^[0-9a-fA-F]{8,64}$')][string]$SnapshotId,
    [ValidateSet('Verify', 'Crypto', 'Data')][string]$Phase = 'Verify',
    [string]$EnvFile,
    [string]$Confirmation,
    [switch]$RealData,
    [switch]$OpenTraffic,
    [string]$TrustEvidenceFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
Assert-BiaiceDocker
$expectedConfirmation = "RESTORE BIAICE $SnapshotId"

Push-Location $root
try {
    & docker compose --env-file $resolvedEnvFile --profile restore run --rm -e "RESTORE_SNAPSHOT=$SnapshotId" restore-verify
    if ($LASTEXITCODE -ne 0) { throw 'Encrypted repository or exact snapshot verification failed.' }
}
finally {
    Pop-Location
}

if ($Phase -eq 'Verify') {
    Write-Host "Snapshot $SnapshotId passed repository verification. No service or volume was modified."
    return
}

if ($Confirmation -ne $expectedConfirmation) {
    throw "Destructive restore requires -Confirmation '$expectedConfirmation'."
}

if ($RealData -and $Phase -eq 'Data') {
    if ([string]::IsNullOrWhiteSpace($TrustEvidenceFile) -or
        -not (Test-Path -LiteralPath $TrustEvidenceFile -PathType Leaf) -or
        (Get-Item -LiteralPath $TrustEvidenceFile).Length -eq 0) {
        throw 'Real-data restore requires non-empty evidence that the original local CA is still trusted by the seven approved devices.'
    }
}

if ($Phase -eq 'Crypto') {
    Push-Location $root
    try {
        & docker compose --env-file $resolvedEnvFile stop gateway web api worker-ingest worker-simulation worker-governance worker-provider scheduler keycloak minio openbao postgres
        if ($LASTEXITCODE -ne 0) { throw 'Could not close application traffic before crypto restore.' }

        & docker compose --env-file $resolvedEnvFile --profile restore run --rm -e "RESTORE_SNAPSHOT=$SnapshotId" restore-fetch
        if ($LASTEXITCODE -ne 0) { throw 'Could not decrypt the exact snapshot into the dedicated restore staging volume.' }

        & docker compose --env-file $resolvedEnvFile --profile restore run --rm -e "RESTORE_SNAPSHOT=$SnapshotId" -e "RESTORE_CONFIRMATION=$expectedConfirmation" restore-crypto-materials
        if ($LASTEXITCODE -ne 0) { throw 'OpenBao/Caddy recovery-material restore failed.' }

        & docker compose --env-file $resolvedEnvFile up --detach openbao
        if ($LASTEXITCODE -ne 0) { throw 'Restored OpenBao could not be started.' }
    }
    finally {
        Pop-Location
    }
    Write-Host 'Crypto phase completed with traffic closed.'
    Write-Host 'Two custodians must now unseal the restored OpenBao with the original 2-of-3 shares and verify its audit device. Then run Phase Data with the same exact snapshot ID.'
    return
}

# Data phase must never proceed with sealed/reinitialized key material.
Push-Location $root
try {
    $baoStatusText = (& docker compose --env-file $resolvedEnvFile exec -T openbao bao status -format=json 2>$null) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'OpenBao status is unavailable; restore fails closed.' }
    $baoStatus = $baoStatusText | ConvertFrom-Json
    if ($baoStatus.sealed -ne $false -or $baoStatus.initialized -ne $true) {
        throw 'OpenBao must be restored, initialized and unsealed before identity or business data.'
    }

    & docker compose --env-file $resolvedEnvFile stop gateway web api worker-ingest worker-simulation worker-governance worker-provider scheduler keycloak minio postgres
    if ($LASTEXITCODE -ne 0) { throw 'Could not keep application traffic closed for data restore.' }

    & docker compose --env-file $resolvedEnvFile --profile restore run --rm -e "RESTORE_SNAPSHOT=$SnapshotId" -e "RESTORE_CONFIRMATION=$expectedConfirmation" restore-identity-materials
    if ($LASTEXITCODE -ne 0) { throw 'Keycloak identity material restore failed.' }

    & docker compose --env-file $resolvedEnvFile up --detach --wait postgres
    if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL did not become healthy for logical restore.' }

    & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'dropdb --if-exists --force --username "$POSTGRES_USER" "$KEYCLOAK_DB"; createdb --username "$POSTGRES_USER" --owner "$KEYCLOAK_DB_USER" "$KEYCLOAK_DB"; PGPASSWORD="$KEYCLOAK_DB_PASSWORD" pg_restore --exit-on-error --no-owner --no-privileges --username "$KEYCLOAK_DB_USER" --dbname "$KEYCLOAK_DB" /backup-staging/keycloak.dump'
    if ($LASTEXITCODE -ne 0) { throw 'Keycloak identity database restore failed.' }

    & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'dropdb --if-exists --force --username "$POSTGRES_USER" "$POSTGRES_DB"; createdb --username "$POSTGRES_USER" --owner "$POSTGRES_USER" "$POSTGRES_DB"; pg_restore --exit-on-error --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" /backup-staging/biaice.dump'
    if ($LASTEXITCODE -ne 0) { throw 'Business database restore failed.' }

    & docker compose --env-file $resolvedEnvFile --profile restore run --rm -e "RESTORE_SNAPSHOT=$SnapshotId" -e "RESTORE_CONFIRMATION=$expectedConfirmation" restore-object-materials
    if ($LASTEXITCODE -ne 0) { throw 'MinIO/audit-anchor material restore failed.' }

    & docker compose --env-file $resolvedEnvFile up --detach --wait redis-broker redis-cache minio keycloak clamav migrate api worker-ingest worker-simulation worker-governance worker-provider scheduler web
    if ($LASTEXITCODE -ne 0) { throw 'Restored core services failed readiness checks; gateway remains closed.' }

    & docker compose --env-file $resolvedEnvFile exec -T api python -m biaice.cli replay-tombstones
    $tombstoneReplayOk = ($LASTEXITCODE -eq 0)
    & docker compose --env-file $resolvedEnvFile exec -T api python -m biaice.cli reconcile-outbox
    $outboxReplayOk = ($LASTEXITCODE -eq 0)
    if ($RealData -and (-not $tombstoneReplayOk -or -not $outboxReplayOk)) {
        throw 'Tombstone/outbox replay did not pass; real-data traffic remains closed to prevent deleted data resurrection.'
    }
    if (-not $tombstoneReplayOk -or -not $outboxReplayOk) {
        Write-Warning 'M0 backend does not yet expose replay commands; synthetic restore is not eligible for REAL_DATA_MODE.'
    }

    if ($OpenTraffic) {
        if ($RealData -and ([string]::IsNullOrWhiteSpace($TrustEvidenceFile) -or -not (Test-Path -LiteralPath $TrustEvidenceFile -PathType Leaf))) {
            throw 'Original local-CA trust evidence is required before opening gateway traffic.'
        }
        & docker compose --env-file $resolvedEnvFile up --detach --wait gateway
        if ($LASTEXITCODE -ne 0) { throw 'Gateway did not become healthy after restore.' }
        Write-Host 'Gateway traffic reopened after explicit request.'
    }
    else {
        Write-Host 'Data phase completed; gateway remains closed pending device trust, deletion non-resurrection, audit-chain and application acceptance checks.'
    }
}
finally {
    Pop-Location
}
