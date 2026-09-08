# דחיפה ל-GitHub: מוסיף שינויים, מבצע commit (אם יש מה לשמור) ודוחף ל-origin.
# שימוש:
#   .\scripts\push-to-github.ps1
#   .\scripts\push-to-github.ps1 -Message "feat: describe the change"
param(
    [Parameter(Position = 0)]
    [string]$Message
)

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

Write-Step "סטטוס לפני דחיפה ($branch)..."
git status --short
Write-Host ""

$hasChanges = [bool](git status --porcelain)
if ($hasChanges) {
    if (-not $Message) {
        $Message = Read-Host "הזן הודעת commit"
    }
    $Message = $Message.Trim()
    if (-not $Message) {
        throw "נדרשת הודעת commit כדי לדחוף שינויים."
    }

    Write-Step "מוסיף קבצים (git add -A)..."
    git add -A

    $staged = [bool](git diff --cached --name-only)
    if (-not $staged) {
        Write-Warn "אין קבצים ב-staging אחרי git add. מדלג על commit."
    }
    else {
        Write-Step "יוצר commit..."
        git commit -m $Message
        Write-Ok "Commit נוצר."
    }
}
else {
    Write-Warn "אין שינויים מקומיים ל-commit."
}

$upstream = git rev-parse --abbrev-ref --symbolic-full-name "@{u}" 2>$null
Write-Step "דוחף ל-GitHub..."
if ($LASTEXITCODE -ne 0 -or -not $upstream) {
    git push -u origin $branch
}
else {
    git push
}

if ($LASTEXITCODE -ne 0) {
    throw "הדחיפה ל-GitHub נכשלה."
}

Write-Ok "הדחיפה ל-GitHub הושלמה בהצלחה (branch: $branch)."
