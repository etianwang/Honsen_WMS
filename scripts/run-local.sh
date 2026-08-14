#!/usr/bin/env bash
# 本地一键启动（macOS/Linux 开发用，不打包 exe/AppImage）：
# 起本地 FastAPI，用 pywebview 打开原生桌面窗口（跟打包后 exe 的体验一致）。
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VENV="$ROOT/.venv"

# 1. Python 虚拟环境
if [ ! -d "$VENV" ]; then
  echo "==> 创建虚拟环境 .venv"
  PY=python3.12
  command -v "$PY" >/dev/null 2>&1 || PY=python3
  "$PY" -m venv "$VENV"
fi

PIP="$VENV/bin/pip"
PY="$VENV/bin/python"

if [ ! -f "$VENV/.deps-installed" ]; then
  echo "==> 安装后端依赖（含 pywebview 原生窗口所需的 pyobjc）"
  "$PIP" install -q -r backend/requirements.txt
  touch "$VENV/.deps-installed"
fi

# 2. 前端静态导出（已存在则跳过；用 --force 强制重新构建）
if [ ! -f "frontend/out/index.html" ] || [ "${1:-}" = "--force" ]; then
  echo "==> 构建前端静态资源"
  command -v npm >/dev/null 2>&1 || { echo "未找到 npm，请先安装 Node.js"; exit 1; }
  [ -d "frontend/node_modules" ] || (cd frontend && npm install)
  (cd frontend && npm run build:desktop)
fi

# 3. 启动桌面窗口（desktop/launcher.py 内部会自选端口、起 uvicorn、开原生窗口）
echo "==> 打开桌面窗口（默认账号 Honsen_Admin / 66778899HONSEN，首次用登录页「初始化数据库」）"
exec "$PY" desktop/launcher.py
