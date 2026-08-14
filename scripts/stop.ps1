[CmdletBinding()]
param(
    [string]$EnvFile,
    [switch]$RemoveVolumes,
    [string]$Confirmation
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
Assert-BiaiceDocker

$arguments = @('down', '--remove-orphans')
if ($RemoveVolumes) {
    if ($Confirmation -ne 'PURGE SYNTHETIC BIAICE') {
        throw 'Volume deletion requires -Confirmation ''PURGE SYNTHETIC BIAICE''.'
    }
    $environment = Read-BiaiceEnv -Path $resolvedEnvFile
    if ($environment.GATEWAY_HOST_PORT -ne '8080') {
        throw 'Refusing volume purge because this is not the fixed synthetic HTTP profile.'
    }
    $arguments += '--volumes'
}

Invoke-BiaiceCompose -Root $root -EnvFile $resolvedEnvFile -Arguments $arguments | Out-Null
if ($RemoveVolumes) {
    Write-Host 'Stopped the stack and removed only Compose-labeled project volumes. This data is recoverable only from a verified encrypted backup.'
}
else {
    Write-Host 'Stopped the stack. Named data and local-CA volumes were preserved.'
}
