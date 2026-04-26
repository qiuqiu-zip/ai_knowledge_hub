#!/usr/bin/env bash
set -euo pipefail

if ! command -v docker >/dev/null 2>&1; then
  echo "[ERROR] docker 未安装或不在 PATH 中"
  exit 1
fi

if ! docker compose version >/dev/null 2>&1; then
  echo "[ERROR] docker compose 不可用"
  exit 1
fi

wait_for_docker() {
  local retries="${DOCKER_WAIT_SECONDS:-180}"
  local i
  for i in $(seq 1 "$retries"); do
    if docker info >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  return 1
}

if ! docker info >/dev/null 2>&1; then
  echo "[WARN] Docker daemon 未启动，尝试自动拉起..."
  if command -v open >/dev/null 2>&1; then
    open -a Docker >/dev/null 2>&1 || open /Applications/Docker.app >/dev/null 2>&1 || true
  fi
  if ! wait_for_docker; then
    echo "[ERROR] 无法连接 Docker daemon。请先启动 Docker Desktop 后重试。"
    echo "        可尝试手动执行: open -a Docker"
    exit 1
  fi
fi

if [ ! -f ".env" ]; then
  if [ -f ".env.example" ]; then
    cp .env.example .env
    echo "[SkillVault] 检测到 .env 不存在，已自动从 .env.example 创建"
  else
    echo "[ERROR] .env 和 .env.example 都不存在"
    exit 1
  fi
fi

MODE="${1:-all}"

case "$MODE" in
  all)
    echo "[SkillVault] 启动前端 + 后端 + worker + scheduler + postgres"
    docker compose up --build
    ;;
  backend)
    echo "[SkillVault] 启动后端链路 (postgres + backend + worker + scheduler)"
    docker compose up --build postgres backend worker scheduler
    ;;
  frontend)
    echo "[SkillVault] 启动前端"
    docker compose up --build frontend
    ;;
  down)
    echo "[SkillVault] 停止全部服务"
    docker compose down
    ;;
  *)
    echo "用法: ./start.sh [all|backend|frontend|down]"
    exit 1
    ;;
esac
