# Honsen WMS desktop build script (ASCII-safe for Windows PowerShell)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> Install Python deps"
python -m pip install -r "$Root\backend\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "pip install requirements failed" }
python -m pip install pillow pyinstaller
if ($LASTEXITCODE -ne 0) { throw "pip install pillow/pyinstaller failed" }

Write-Host "==> Build app icon logo.ico"
python "$Root\scripts\build_app_icon.py"
if ($LASTEXITCODE -ne 0) { throw "build_app_icon failed" }

Write-Host "==> Build React frontend (static export)"
Push-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }
npm run build:desktop
if ($LASTEXITCODE -ne 0) { throw "frontend build failed" }
Pop-Location

Write-Host "==> PyInstaller package exe"
Push-Location "$Root"
pyinstaller "$Root\desktop\honsen_wms.spec" --noconfirm
if ($LASTEXITCODE -ne 0) { throw "pyinstaller failed" }
Pop-Location

$Dist = Join-Path $Root "dist"
$DistDb = Join-Path $Dist "db"

if (Test-Path $DistDb) {
    Write-Host "==> Clean dist\db"
    Remove-Item $DistDb -Recurse -Force
}
Write-Host "==> Create empty dist\db"
New-Item -ItemType Directory -Path $DistDb -Force | Out-Null

$ExeName = "Honsen海外仓库管理同步版.exe"
Write-Host ("Done: " + (Join-Path $Dist $ExeName))
Write-Host "Note: dist\db is empty; init DB from login page on first run."

Write-Host "==> Assemble portable zip (no WebView2)"
python "$Root\scripts\assemble_portable.py"
if ($LASTEXITCODE -ne 0) { throw "assemble_portable failed" }
