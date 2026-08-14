[CmdletBinding()]
param(
    [string]$EnvFile,
    [switch]$Force,
    [switch]$RotateSyntheticPasswords
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

function New-BiaiceRandomSecret {
    param([int]$ByteCount = 32)
    $bytes = New-Object byte[] $ByteCount
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

function New-BiaiceSyntheticUserPassword {
    # Keycloak's synthetic realm requires all four character classes.  A
    # Base64URL secret alone does not guarantee a digit or special character.
    return "Aa1!$(New-BiaiceRandomSecret)"
}

function Test-BiaiceSyntheticUserPassword {
    param([string]$Value)
    return (
        $Value.Length -ge 14 -and
        $Value -cmatch '[A-Z]' -and
        $Value -cmatch '[a-z]' -and
        $Value -match '[0-9]' -and
        $Value -match '[^A-Za-z0-9]'
    )
}

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
$template = Join-Path $root '.env.example'
if (-not (Test-Path -LiteralPath $template -PathType Leaf)) {
    throw "Missing template: $template"
}

$generatedSecrets = [ordered]@{
    POSTGRES_PASSWORD = '__GENERATE_POSTGRES_PASSWORD__'
    POSTGRES_MIGRATION_PASSWORD = '__GENERATE_POSTGRES_MIGRATION_PASSWORD__'
    POSTGRES_RUNTIME_PASSWORD = '__GENERATE_POSTGRES_RUNTIME_PASSWORD__'
    KEYCLOAK_DB_PASSWORD = '__GENERATE_KEYCLOAK_DB_PASSWORD__'
    REDIS_BROKER_PASSWORD = '__GENERATE_REDIS_BROKER_PASSWORD__'
    REDIS_CACHE_PASSWORD = '__GENERATE_REDIS_CACHE_PASSWORD__'
    MINIO_ROOT_PASSWORD = '__GENERATE_MINIO_ROOT_PASSWORD__'
    KEYCLOAK_ADMIN_PASSWORD = '__GENERATE_KEYCLOAK_ADMIN_PASSWORD__'
    GRAFANA_ADMIN_PASSWORD = '__GENERATE_GRAFANA_ADMIN_PASSWORD__'
}

if ((Test-Path -LiteralPath $resolvedEnvFile) -and -not $Force) {
    $content = Get-Content -LiteralPath $resolvedEnvFile -Raw -Encoding utf8
    $existing = Read-BiaiceEnv -Path $resolvedEnvFile
    $changed = $false
    foreach ($entry in $generatedSecrets.GetEnumerator()) {
        if ($content.Contains($entry.Value)) {
            $content = $content.Replace($entry.Value, (New-BiaiceRandomSecret))
            $changed = $true
        }
        elseif (-not $existing.ContainsKey($entry.Key)) {
            $content = $content.TrimEnd() + "`n$($entry.Key)=$(New-BiaiceRandomSecret)`n"
            $changed = $true
        }
    }
    if ($changed) {
        [System.IO.File]::WriteAllText($resolvedEnvFile, $content, (New-Object System.Text.UTF8Encoding($false)))
        Protect-BiaiceLocalFile -Path $resolvedEnvFile
        Write-Host "Upgraded existing local environment without rotating existing credentials: $resolvedEnvFile"
    }
    else {
        Write-Host "Keeping existing local environment: $resolvedEnvFile"
    }
}
else {
    if ($Force) {
        $projectName = 'biaice'
        if (Test-Path -LiteralPath $resolvedEnvFile) {
            $existing = Read-BiaiceEnv -Path $resolvedEnvFile
            if ($existing.ContainsKey('COMPOSE_PROJECT_NAME')) { $projectName = $existing.COMPOSE_PROJECT_NAME }
        }
        $existingVolumes = & docker volume ls --quiet --filter "label=com.docker.compose.project=$projectName" 2>$null
        if ($LASTEXITCODE -eq 0 -and @($existingVolumes).Count -gt 0) {
            throw 'Refusing to rotate local infrastructure passwords while project volumes exist. Back up and remove the exact synthetic project volumes first.'
        }
    }

    $content = Get-Content -LiteralPath $template -Raw -Encoding utf8
    foreach ($placeholder in $generatedSecrets.Values) {
        $content = $content.Replace($placeholder, (New-BiaiceRandomSecret))
    }
    [System.IO.File]::WriteAllText($resolvedEnvFile, $content, (New-Object System.Text.UTF8Encoding($false)))
    Protect-BiaiceLocalFile -Path $resolvedEnvFile
    Write-Host "Created ignored synthetic-only environment: $resolvedEnvFile"
}

$validatedContent = Get-Content -LiteralPath $resolvedEnvFile -Raw -Encoding utf8
if ($validatedContent -match '__GENERATE_[A-Z0-9_]+__') {
    throw 'The local environment still contains an unresolved secret placeholder.'
}

$secretDirectory = Join-Path $root 'infra\secrets'
$keycloakGenerated = Join-Path $root 'infra\keycloak\generated'
$openbaoGenerated = Join-Path $root 'infra\openbao\generated'
$egressGenerated = Join-Path $root 'infra\provider-egress\generated'
foreach ($directory in @($secretDirectory, $keycloakGenerated, $openbaoGenerated, $egressGenerated)) {
    $null = New-Item -ItemType Directory -Path $directory -Force
}

$resticPasswordFile = Join-Path $secretDirectory 'restic-password.txt'
if (-not (Test-Path -LiteralPath $resticPasswordFile -PathType Leaf)) {
    [System.IO.File]::WriteAllText($resticPasswordFile, (New-BiaiceRandomSecret 48), (New-Object System.Text.UTF8Encoding($false)))
    Protect-BiaiceLocalFile -Path $resticPasswordFile
}

$testUsersFile = Join-Path $keycloakGenerated 'test-users.env'
$testUserPasswords = @{}
if (Test-Path -LiteralPath $testUsersFile -PathType Leaf) {
    foreach ($line in Get-Content -LiteralPath $testUsersFile -Encoding utf8) {
        if ($line -match '^(BIAICE_M[1-7]_PASSWORD)=(.+)$') {
            $testUserPasswords[$Matches[1]] = $Matches[2]
        }
    }
}
$testUsersChanged = $false
$lines = for ($member = 1; $member -le 7; $member++) {
    $name = "BIAICE_M${member}_PASSWORD"
    $password = $testUserPasswords[$name]
    if ($RotateSyntheticPasswords -or -not (Test-BiaiceSyntheticUserPassword -Value $password)) {
        $password = New-BiaiceSyntheticUserPassword
        $testUsersChanged = $true
    }
    "${name}=$password"
}
if ($testUsersChanged -or -not (Test-Path -LiteralPath $testUsersFile -PathType Leaf)) {
    # The file is consumed by Bash inside the Keycloak init container.  Write
    # LF explicitly so a Windows CR is never interpreted as part of a password.
    [System.IO.File]::WriteAllText(
        $testUsersFile,
        (($lines -join "`n") + "`n"),
        (New-Object System.Text.UTF8Encoding($false))
    )
    Protect-BiaiceLocalFile -Path $testUsersFile
    if ($RotateSyntheticPasswords) {
        Write-Host 'Rotated only the seven synthetic test-user passwords.'
    }
    else {
        Write-Host 'Created or upgraded policy-compliant synthetic test-user passwords.'
    }
}

Assert-BiaiceIgnored -Root $root -Path $resolvedEnvFile
Assert-BiaiceIgnored -Root $root -Path $resticPasswordFile
Assert-BiaiceIgnored -Root $root -Path $testUsersFile

$environment = Read-BiaiceEnv -Path $resolvedEnvFile
Write-Host 'Initialization completed. No API key, OpenBao root token, or unseal share was created or stored.'
Write-BiaiceUrls -Environment $environment
Write-Host 'Configure biaice.local in LAN DNS or each test device hosts file before cross-device testing.'
