[CmdletBinding()]
param(
    [string]$EnvFile,
    [switch]$StaticOnly
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'lib\common.ps1')

$root = Get-BiaiceRoot
$resolvedEnvFile = Get-BiaiceEnvFile -Root $root -EnvFile $EnvFile
if (-not (Test-Path -LiteralPath $resolvedEnvFile -PathType Leaf)) {
    $resolvedEnvFile = Join-Path $root '.env.example'
}
Assert-BiaiceDocker

Push-Location $root
try {
    & docker compose --env-file $resolvedEnvFile --profile '*' config --quiet
    if ($LASTEXITCODE -ne 0) { throw 'docker compose config validation failed.' }

    $jsonText = (& docker compose --env-file $resolvedEnvFile --profile '*' config --format json) -join "`n"
    if ($LASTEXITCODE -ne 0) { throw 'Could not render normalized Compose JSON.' }
    $config = $jsonText | ConvertFrom-Json

    $requiredServices = @(
        'gateway', 'web', 'api', 'worker-ingest', 'worker-simulation',
        'worker-governance', 'worker-provider', 'scheduler', 'postgres',
        'redis-broker', 'redis-cache', 'minio', 'keycloak', 'openbao',
        'clamav', 'provider-egress-gateway'
    )
    foreach ($serviceName in $requiredServices) {
        if ($null -eq $config.services.PSObject.Properties[$serviceName]) {
            throw "Missing required Compose service: $serviceName"
        }
    }

    foreach ($property in $config.services.PSObject.Properties) {
        $portsProperty = $property.Value.PSObject.Properties['ports']
        if ($null -ne $portsProperty -and @($portsProperty.Value).Count -gt 0 -and $property.Name -ne 'gateway') {
            throw "Only gateway may publish host ports; found: $($property.Name)"
        }
    }

    foreach ($networkName in @('host-ingress', 'front', 'back', 'provider-egress', 'maintenance-egress')) {
        if ($null -eq $config.networks.PSObject.Properties[$networkName]) {
            throw "Missing required network: $networkName"
        }
    }
    if ($config.networks.front.internal -ne $true -or $config.networks.back.internal -ne $true) {
        throw 'front and back must be internal networks.'
    }
    $hostIngressInternal = $config.networks.'host-ingress'.PSObject.Properties['internal']
    if ($null -ne $hostIngressInternal -and $hostIngressInternal.Value -eq $true) {
        throw 'host-ingress must be host-routable.'
    }
    $providerInternal = $config.networks.'provider-egress'.PSObject.Properties['internal']
    $maintenanceInternal = $config.networks.'maintenance-egress'.PSObject.Properties['internal']
    if (($null -ne $providerInternal -and $providerInternal.Value -eq $true) -or
        ($null -ne $maintenanceInternal -and $maintenanceInternal.Value -eq $true)) {
        throw 'The two explicit egress networks must be routable; membership is the deny-by-default control.'
    }

    foreach ($property in $config.services.PSObject.Properties) {
        $networksProperty = $property.Value.PSObject.Properties['networks']
        $networkNames = if ($null -eq $networksProperty) { @() } else { @($networksProperty.Value.PSObject.Properties.Name) }
        if ($networkNames -contains 'provider-egress' -and $property.Name -ne 'provider-egress-gateway') {
            throw "Unexpected provider-egress network member: $($property.Name)"
        }
        if ($networkNames -contains 'maintenance-egress' -and $property.Name -ne 'clamav-signature-update') {
            throw "Unexpected maintenance-egress network member: $($property.Name)"
        }
        if ($networkNames -contains 'host-ingress' -and $property.Name -ne 'gateway') {
            throw "Unexpected host-ingress network member: $($property.Name)"
        }
    }

    $providerProfiles = @($config.services.'provider-egress-gateway'.profiles)
    if ($providerProfiles -notcontains 'provider-egress') {
        throw 'provider-egress-gateway must remain behind its explicit profile.'
    }

    foreach ($serviceName in @('api', 'web', 'worker-ingest', 'worker-simulation', 'worker-governance', 'worker-provider')) {
        $environment = $config.services.$serviceName.environment
        if ($environment.REAL_DATA_MODE -ne 'false' -or
            $environment.BIAICE_REAL_DATA_MODE_REQUESTED -ne 'false' -or
            $environment.PROVIDER_EGRESS_ENABLED -ne 'false' -or
            $environment.BYOK_SECRET_GATE -ne 'FAIL' -or
            $environment.BIAICE_BYOK_ENABLED -ne 'false') {
            throw "Default fail-closed environment was weakened for $serviceName."
        }
    }

    foreach ($property in $config.services.PSObject.Properties) {
        $imageProperty = $property.Value.PSObject.Properties['image']
        if ($null -ne $imageProperty -and $imageProperty.Value -match '(^|:)latest$') {
            throw "Floating latest image tag is forbidden: $($property.Name)"
        }
    }

    $topologyValidator = Join-Path $root 'scripts\validate_compose_topology.py'
    if (Test-Path -LiteralPath $topologyValidator -PathType Leaf) {
        & python $topologyValidator
        if ($LASTEXITCODE -ne 0) { throw 'Compose topology validator failed.' }
    }

    if (-not $StaticOnly) {
        if (Test-Path -LiteralPath (Join-Path $root 'apps\backend\pyproject.toml')) {
            & python -m pytest apps/backend/tests
            if ($LASTEXITCODE -ne 0) { throw 'Backend tests failed.' }
        }
        if (Test-Path -LiteralPath (Join-Path $root 'apps\web\package.json')) {
            & npm --prefix apps/web test -- --run
            if ($LASTEXITCODE -ne 0) { throw 'Web tests failed.' }
        }
    }
}
finally {
    Pop-Location
}

Write-Host 'Compose topology and requested test suites passed.'
