# משיכה מ-GitHub: מעדכן את הפרויקט המקומי מה-branch הנוכחי ב-origin.
# שימוש:
#   .\scripts\pull-from-github.ps1
$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

function Write-Step([string]$Text) {
    Write-Host $Text -ForegroundColor Cyan
}

function Write-Ok([string]$Text) {
    Write-Host $Text -ForegroundColor Green
}

function Write-Warn([string]$Text) {
    Write-Host $Text -ForegroundColor Yellow
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "git לא מותקן או לא נמצא ב-PATH."
}

$branch = (git rev-parse --abbrev-ref HEAD).Trim()
if (-not $branch) {
    throw "לא נמצא branch נוכחי."
}

$dirty = [bool](git status --porcelain)
if ($dirty) {
    Write-Warn "יש שינויים מקומיים שלא נשמרו. git pull עלול להיכשל אם יש התנגשות."
    git status --short
    Write-Host ""
}

Write-Step "מושך עדכונים מ-GitHub (origin/$branch)..."
git pull --ff-only origin $branch
if ($LASTEXITCODE -ne 0) {
    throw "המשיכה מ-GitHub נכשלה. בדוק קונפליקטים או שינויים מקומיים."
}

Write-Ok "הפרויקט עודכן מ-GitHub (branch: $branch)."
git status -sb
