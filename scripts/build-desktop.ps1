# Honsen WMS 桌面版构建脚本
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> 安装 Python 依赖"
python -m pip install -r "$Root\backend\requirements.txt"

Write-Host "==> 构建 React 前端 (静态导出)"
Push-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) { npm install }
npm run build:desktop
Pop-Location

Write-Host "==> PyInstaller 打包 exe"
Push-Location "$Root"
pyinstaller "$Root\desktop\honsen_wms.spec" --noconfirm
Pop-Location

$Dist = Join-Path $Root "dist"
$DbSrc = Join-Path $Root "db"
if (Test-Path $DbSrc) {
    Write-Host "==> 复制 db 到 dist"
    Copy-Item $DbSrc (Join-Path $Dist "db") -Recurse -Force
}

Write-Host "完成: $Dist\Honsen WMS.exe"
