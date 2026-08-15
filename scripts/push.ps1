# Member-6 push script (PowerShell)
#
# Pushes the feature/m6-simulation branch to GitHub.
#
# Configure ONE of these before running:
#   1. $env:BIAICE_PUSH_TOKEN = "ghp_xxx"   (PAT, scopes: repo + workflow)
#   2. gh auth login                          (uses GCM)
#   3. configure a custom remote via -RemoteUrl
#
# Usage:
#   .\scripts\push.ps1
#   .\scripts\push.ps1 -Branch my-fork -RemoteUrl https://github.com/me/biaice-m6.git

[CmdletBinding()]
param(
    [string]$Branch = "feature/m6-simulation",
    [string]$RemoteUrl = "https://github.com/studynightfive/biaice.git"
)

$ErrorActionPreference = "Stop"

$token = $env:BIAICE_PUSH_TOKEN
if ($token) {
    $authRemote = $RemoteUrl -replace "^https://", "https://x-access-token:$token@"
} else {
    $authRemote = $RemoteUrl
}

$current = git rev-parse --abbrev-ref HEAD
if ($current -ne $Branch) {
    Write-Host "[m6] error: not on $Branch (currently on $current)" -ForegroundColor Red
    exit 1
}

$dirty = git status --porcelain
if ($dirty) {
    Write-Host "[m6] error: working tree is dirty" -ForegroundColor Red
    $dirty | ForEach-Object { Write-Host $_ }
    exit 1
}

$existing = git remote get-url origin 2>$null
if (-not $existing) {
    git remote add origin $authRemote
} else {
    git remote set-url origin $authRemote
}

git push -u origin $Branch

$baseUrl = $RemoteUrl -replace "\.git$", ""
$compareUrl = "$baseUrl/compare/main...$Branch?expand=1"
Write-Host "[m6] pushed. Open a PR at: $compareUrl" -ForegroundColor Green
Write-Host "[m6] Paste docs/delivery/pr-body.md as the PR description."
