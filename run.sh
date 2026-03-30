#!/bin/bash
# local-file-processor 启动脚本
# 运行前自动从 GitHub 拉取最新代码
# 用法：./run.sh [参数传给 main.py]

set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
BRANCH="main"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}[sync] 从 GitHub 拉取最新代码...${NC}"
cd "$REPO_DIR"
git fetch origin --quiet
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse "origin/$BRANCH")
if [ "$LOCAL" != "$REMOTE" ]; then
    git pull origin "$BRANCH"
    echo -e "${GREEN}[sync] 已更新到最新版本${NC}"
else
    echo -e "${GREEN}[sync] 已是最新，无需更新${NC}"
fi

echo -e "${YELLOW}[run] 启动 main.py ...${NC}"
python3 main.py "$@"
