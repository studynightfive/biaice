[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$BundleDirectory,
    [string]$EnvFile,
    [Parameter(Mandatory = $true)][string]$Confirmation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

if ($Confirmation -ne 'IMPORT APPROVED CLAMAV SIGNATURES') {
    throw 'Import requires -Confirmation ''IMPORT APPROVED CLAMAV SIGNATURES''.'
}

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
$bundle = [System.IO.Path]::GetFullPath($BundleDirectory)
$normalizedRoot = [System.IO.Path]::GetFullPath($root).TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
if ($bundle.StartsWith($normalizedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw 'The approved offline bundle must be outside the repository.'
}
if (-not (Test-Path -LiteralPath $bundle -PathType Container)) {
    throw "Bundle directory not found: $bundle"
}
foreach ($required in @('SHA256SUMS', 'APPROVED-OFFLINE-BUNDLE')) {
    if (-not (Test-Path -LiteralPath (Join-Path $bundle $required) -PathType Leaf)) {
        throw "Bundle is missing $required."
    }
}
if (@(Get-ChildItem -LiteralPath $bundle -File | Where-Object { $_.Extension -in @('.cvd', '.cld') }).Count -eq 0) {
    throw 'Bundle has no .cvd or .cld signature database.'
}

Assert-BiaiceDocker
$previousImportDirectory = $env:CLAMAV_SIGNATURE_IMPORT_DIR
try {
    $env:CLAMAV_SIGNATURE_IMPORT_DIR = $bundle
    Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments @('stop', 'clamav') -AllowFailure | Out-Null
    Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments @('--profile', 'maintenance-import', 'run', '--rm', 'clamav-signature-import') | Out-Null
    Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments @('up', '--detach', '--wait', 'clamav') | Out-Null
}
finally {
    $env:CLAMAV_SIGNATURE_IMPORT_DIR = $previousImportDirectory
}

Write-Host 'ClamAV accepted the approved offline signatures and passed its signature-aware healthcheck.'
