# Honsen WMS 桌面版构建脚本
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host "==> 安装 Python 依赖"
python -m pip install -r "$Root\backend\requirements.txt"
python -m pip install pillow

Write-Host "==> 生成多尺寸应用图标 logo.ico"
python "$Root\scripts\build_app_icon.py"

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
$DistDb = Join-Path $Dist "db"

# 交付包不带开发/调试数据库，仅保留空 db 目录供首次运行初始化
if (Test-Path $DistDb) {
    Write-Host "==> 清理 dist\db（移除调试数据）"
    Remove-Item $DistDb -Recurse -Force
}
Write-Host "==> 创建空 db 目录（客户首次登录页初始化）"
New-Item -ItemType Directory -Path $DistDb -Force | Out-Null

Write-Host "完成: $Dist\Honsen WMS.exe"
Write-Host "说明: dist\db 为空，客户运行 exe 后在登录页点击「初始化数据库」"
