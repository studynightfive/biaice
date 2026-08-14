Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-BiaiceRoot {
    return [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
}

function Get-BiaiceEnvFile {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [string]$EnvFile
    )

    if ([string]::IsNullOrWhiteSpace($EnvFile)) {
        return (Join-Path $Root '.env.local')
    }
    if ([System.IO.Path]::IsPathRooted($EnvFile)) {
        return [System.IO.Path]::GetFullPath($EnvFile)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $Root $EnvFile))
}

function Assert-BiaiceDocker {
    $null = Get-Command docker -ErrorAction Stop
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Desktop is not running or the current user cannot access it.'
    }
    & docker compose version *> $null
    if ($LASTEXITCODE -ne 0) {
        throw 'Docker Compose v2 is required.'
    }
}

function Read-BiaiceEnv {
    param([Parameter(Mandatory = $true)][string]$Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Environment file not found: $Path"
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $Path -Encoding utf8) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith('#') -or -not $trimmed.Contains('=')) {
            continue
        }
        $name, $value = $trimmed.Split('=', 2)
        $values[$name.Trim()] = $value.Trim()
    }
    return $values
}

function Test-BiaicePlaceholder {
    param([AllowNull()][string]$Value)
    return [string]::IsNullOrWhiteSpace($Value) -or $Value -match '^__.+__$'
}

function Get-BiaiceLanIPv4 {
    $addresses = @()
    try {
        $configs = Get-NetIPConfiguration -ErrorAction Stop |
            Where-Object { $_.NetAdapter.Status -eq 'Up' -and $null -ne $_.IPv4DefaultGateway }
        foreach ($config in $configs) {
            foreach ($entry in @($config.IPv4Address)) {
                if ($null -ne $entry -and
                    $entry.IPAddress -notlike '127.*' -and
                    $entry.IPAddress -notlike '169.254.*') {
                    $addresses += $entry.IPAddress
                }
            }
        }
    }
    catch {
        $addresses = Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue |
            Where-Object {
                $_.AddressState -eq 'Preferred' -and
                $_.IPAddress -notlike '127.*' -and
                $_.IPAddress -notlike '169.254.*'
            } |
            Select-Object -ExpandProperty IPAddress
    }
    return @($addresses | Select-Object -Unique)
}

function Write-BiaiceUrls {
    param([Parameter(Mandatory = $true)][hashtable]$Environment)

    $port = if ($Environment.ContainsKey('GATEWAY_HOST_PORT')) { $Environment.GATEWAY_HOST_PORT } else { '8080' }
    $scheme = if ($port -eq '8443') { 'https' } else { 'http' }
    Write-Host "Local URL : ${scheme}://localhost:${port}"
    Write-Host "Stable URL: ${scheme}://biaice.local:${port}"

    $lanAddresses = @(Get-BiaiceLanIPv4)
    if ($lanAddresses.Count -eq 0) {
        Write-Warning 'No active LAN IPv4 address was detected. The stable biaice.local URL still requires DNS/hosts configuration.'
    }
    else {
        foreach ($address in $lanAddresses) {
            Write-Host "LAN probe  : ${scheme}://${address}:${port}"
        }
    }
}

function Protect-BiaiceLocalFile {
    param([Parameter(Mandatory = $true)][string]$Path)

    if ($PSVersionTable.PSEdition -eq 'Core' -and -not $IsWindows) {
        & chmod 600 -- $Path *> $null
        return
    }
    try {
        & icacls.exe $Path /inheritance:r /grant:r "${env:USERNAME}:(R,W)" *> $null
    }
    catch {
        Write-Warning "Could not tighten ACL automatically for $Path. Restrict it to the current operator before real-data use."
    }
}

function Assert-BiaiceIgnored {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$Path
    )
    Push-Location $Root
    try {
        & git check-ignore --quiet -- $Path
        if ($LASTEXITCODE -ne 0) {
            throw "Local secret path is not ignored by Git: $Path"
        }
    }
    finally {
        Pop-Location
    }
}

function Invoke-BiaiceCompose {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][string]$EnvFile,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [switch]$AllowFailure
    )
    Push-Location $Root
    try {
        & docker compose --env-file $EnvFile @Arguments
        $exitCode = $LASTEXITCODE
    }
    finally {
        Pop-Location
    }
    if ($exitCode -ne 0 -and -not $AllowFailure) {
        throw "docker compose failed with exit code ${exitCode}: $($Arguments -join ' ')"
    }
    return $exitCode
}

function Invoke-BiaiceLocalImageBuilds {
    param(
        [Parameter(Mandatory = $true)][string]$Root,
        [Parameter(Mandatory = $true)][hashtable]$Environment
    )

    $tag = if ($Environment.ContainsKey('BIAICE_IMAGE_TAG')) { $Environment.BIAICE_IMAGE_TAG } else { 'local' }
    if ($tag -notmatch '^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$') {
        throw 'BIAICE_IMAGE_TAG contains unsupported characters.'
    }
    $builds = @(
        @{ Image = "biaice/backend:${tag}"; Dockerfile = 'infra/compose/backend.Dockerfile' },
        @{ Image = "biaice/web:${tag}"; Dockerfile = 'infra/compose/web.Dockerfile' },
        @{ Image = "biaice/keycloak:${tag}"; Dockerfile = 'infra/keycloak/Dockerfile' },
        @{ Image = "biaice/provider-egress:${tag}"; Dockerfile = 'infra/provider-egress/Dockerfile' }
    )

    Push-Location $Root
    try {
        foreach ($build in $builds) {
            & docker build --file $build.Dockerfile --tag $build.Image .
            if ($LASTEXITCODE -ne 0) {
                throw "Docker image build failed: $($build.Image)"
            }
        }
    }
    finally {
        Pop-Location
    }
}
