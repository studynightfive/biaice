[CmdletBinding()]
param(
    [string]$EnvFile,
    [switch]$Observability,
    [switch]$SkipBuild,
    [switch]$SkipSeed
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile

& (Join-Path $PSScriptRoot 'init.ps1') -EnvFile $resolvedEnvFile
Assert-BiaiceDocker
$environment = Read-BiaiceEnv -Path $resolvedEnvFile

if ($environment.GATEWAY_HOST_PORT -ne '8080' -or $environment.GATEWAY_CONTAINER_PORT -ne '8080') {
    throw 'scripts/dev.ps1 only starts the fail-closed HTTP/synthetic profile on port 8080.'
}

$arguments = @()
if ($Observability) { $arguments += @('--profile', 'observability') }
$arguments += @('up', '--detach', '--wait')
if (-not $SkipBuild) {
    # Explicit builds are reliable across Windows workspace path encodings and
    # produce exactly the image names consumed by Compose.
    Invoke-BiaiceLocalImageBuilds -Root $root -Environment $environment
}

Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments $arguments | Out-Null
Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments @('--profile', 'init', 'run', '--rm', 'keycloak-init') | Out-Null
if (-not $SkipSeed) {
    Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments @('--profile', 'seed', 'run', '--rm', 'seed-synthetic') | Out-Null
}

Write-Host ''
Write-Host 'Biaice synthetic development stack is ready.'
Write-BiaiceUrls -Environment $environment
Write-Host ''
Write-Host 'Safety state: REAL_DATA_MODE=false, BYOK_SECRET_GATE=FAIL, credential endpoints disabled, Provider egress profile not started.'
Write-Host 'OpenBao is a non-dev Raft server; initialized/sealed state is not treated as a passing security Gate.'
Push-Location $root
try {
    & docker compose --env-file $resolvedEnvFile ps
}
finally {
    Pop-Location
}
