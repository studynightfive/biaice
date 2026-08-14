[CmdletBinding()]
param(
    [string]$EnvFile,
    [switch]$RealData,
    [string]$TrustedTimeEvidenceFile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
Assert-BiaiceDocker
$environment = Read-BiaiceEnv -Path $resolvedEnvFile

$passwordPath = $environment.BIAICE_BACKUP_PASSWORD_FILE
if (-not [System.IO.Path]::IsPathRooted($passwordPath)) {
    $passwordPath = [System.IO.Path]::GetFullPath((Join-Path $root $passwordPath))
}
if (-not (Test-Path -LiteralPath $passwordPath -PathType Leaf) -or (Get-Item -LiteralPath $passwordPath).Length -lt 32) {
    throw 'A non-placeholder restic password file of at least 32 bytes is required.'
}

if ($RealData) {
    $normalizedRoot = [System.IO.Path]::GetFullPath($root).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    $normalizedPassword = [System.IO.Path]::GetFullPath($passwordPath)
    if ($normalizedPassword.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Real-data backup encryption material must be outside the repository and a separate trust domain.'
    }
    if ([string]::IsNullOrWhiteSpace($TrustedTimeEvidenceFile) -or
        -not (Test-Path -LiteralPath $TrustedTimeEvidenceFile -PathType Leaf)) {
        throw 'Real-data backup requires a trusted-time evidence file.'
    }
    $operatorDirectory = if ($environment.ContainsKey('BIAICE_OPENBAO_OPERATOR_DIR')) {
        $environment.BIAICE_OPENBAO_OPERATOR_DIR
    }
    else {
        './infra/openbao/generated'
    }
    if (-not [System.IO.Path]::IsPathRooted($operatorDirectory)) {
        $operatorDirectory = [System.IO.Path]::GetFullPath((Join-Path $root $operatorDirectory))
    }
    if ([System.IO.Path]::GetFullPath($operatorDirectory).StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw 'Real-data OpenBao operator credentials must be mounted from outside the repository/trust domain.'
    }
    $backupTokenFile = Join-Path $operatorDirectory 'backup-token'
    if (-not (Test-Path -LiteralPath $backupTokenFile -PathType Leaf) -or (Get-Item -LiteralPath $backupTokenFile).Length -eq 0) {
        throw 'A short-lived, least-privilege OpenBao backup token file is required for real-data backup.'
    }
}

$freezeStarted = $false
try {
    Push-Location $root
    try {
        & docker compose --env-file $resolvedEnvFile exec -T api python -m biaice.cli freeze begin --reason encrypted-backup
        $freezeStarted = ($LASTEXITCODE -eq 0)
    }
    finally {
        Pop-Location
    }
    if ($RealData -and -not $freezeStarted) {
        throw 'The API did not acknowledge the freeze barrier; real-data backup is blocked.'
    }
    if (-not $freezeStarted) {
        Write-Warning 'Freeze command is not implemented/available; continuing is allowed only for the synthetic M0 baseline.'
    }

    $backupId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ')
    Push-Location $root
    try {
        $gitRevision = (& git rev-parse HEAD 2>$null) -join ''
        if ($LASTEXITCODE -ne 0) { $gitRevision = 'unversioned' }
    }
    finally {
        Pop-Location
    }
    $trustedTimeEvidenceHash = if ($RealData) {
        (Get-FileHash -LiteralPath $TrustedTimeEvidenceFile -Algorithm SHA256).Hash.ToLowerInvariant()
    }
    else {
        $null
    }
    $manifest = [ordered]@{
        schema_version = 1
        backup_id = $backupId
        trusted_utc = [DateTime]::UtcNow.ToString('o')
        git_revision = $gitRevision
        deployment_mode = $(if ($RealData) { 'REAL_DATA' } else { 'SYNTHETIC_ONLY' })
        freeze_barrier = $freezeStarted
        trusted_time_evidence_sha256 = $trustedTimeEvidenceHash
        restore_order = @('openbao', 'caddy-local-ca', 'keycloak', 'postgres', 'minio', 'audit-anchors', 'tombstone-outbox-replay')
        plaintext_secret_in_manifest = $false
    } | ConvertTo-Json -Depth 4 -Compress

    Push-Location $root
    try {
        & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'find /backup-staging -mindepth 1 -maxdepth 1 -type f -delete'
        if ($LASTEXITCODE -ne 0) { throw 'Could not clear the dedicated backup staging volume.' }

        $manifest | & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'umask 077; cat > /backup-staging/manifest.json'
        if ($LASTEXITCODE -ne 0) { throw 'Could not write backup manifest to staging.' }

        & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'umask 077; pg_dump --format=custom --no-owner --no-privileges --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --file /backup-staging/biaice.dump'
        if ($LASTEXITCODE -ne 0) { throw 'PostgreSQL business database backup failed.' }

        & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'umask 077; PGPASSWORD="$KEYCLOAK_DB_PASSWORD" pg_dump --format=custom --no-owner --no-privileges --username "$KEYCLOAK_DB_USER" --dbname "$KEYCLOAK_DB" --file /backup-staging/keycloak.dump'
        if ($LASTEXITCODE -ne 0) { throw 'Keycloak database backup failed.' }

        & docker compose --env-file $resolvedEnvFile exec -T openbao sh -ceu 'test -s /run/biaice-openbao/backup-token; BAO_TOKEN="$(cat /run/biaice-openbao/backup-token)" bao operator raft snapshot save /backup-staging/openbao.snap'
        $openbaoSnapshotOk = ($LASTEXITCODE -eq 0)
        if ($RealData -and -not $openbaoSnapshotOk) {
            throw 'OpenBao Raft snapshot failed; raw live storage is not accepted for real-data recovery.'
        }
        if (-not $openbaoSnapshotOk) {
            Write-Warning 'OpenBao is uninitialized/sealed or lacks the short-lived backup token; no logical Raft snapshot was added to this synthetic backup.'
        }

        & docker compose --env-file $resolvedEnvFile --profile backup run --rm backup
        if ($LASTEXITCODE -ne 0) { throw 'Encrypted restic backup or integrity check failed.' }
    }
    finally {
        Pop-Location
    }

    Write-Host "Encrypted backup completed: $backupId"
    Write-Host 'The repository is a named Docker volume. Export/copy it to approved encrypted offline or off-host custody; do not co-locate it with the password or OpenBao shares.'
}
finally {
    Push-Location $root
    try {
        & docker compose --env-file $resolvedEnvFile exec -T postgres sh -ceu 'find /backup-staging -mindepth 1 -maxdepth 1 -type f -delete' *> $null
        if ($freezeStarted) {
            & docker compose --env-file $resolvedEnvFile exec -T api python -m biaice.cli freeze end --reason encrypted-backup *> $null
            if ($LASTEXITCODE -ne 0) {
                Write-Warning 'Backup completed/failed, but the API freeze barrier could not be released automatically. Keep gateway closed and resolve it manually.'
            }
        }
    }
    finally {
        Pop-Location
    }
}
