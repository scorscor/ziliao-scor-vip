param(
    [Parameter(Position = 0)]
    [string]$Message
)

$ErrorActionPreference = "Stop"

Set-Location -LiteralPath $PSScriptRoot

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git is not installed or not available in PATH."
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    throw "Unable to detect the current Git branch."
}

$statusLines = git status --porcelain
if (-not $statusLines) {
    Write-Host "No changes detected. Nothing to commit."
    exit 0
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "a"
}

Write-Host "Branch: $branch"
Write-Host "Commit message: $Message"

git add .
git commit -m $Message

$upstream = git rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>$null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($upstream)) {
    git push -u origin $branch
}
else {
    git push
}
