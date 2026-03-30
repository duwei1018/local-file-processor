#!/usr/bin/env bash
# backup.sh — 一键备份 local-file-processor 并推送到 GitHub
#
# 使用方法：
#   ./backup.sh "本次修改的简要说明"
#
# 执行步骤：
#   1. 追加一条变更记录到 CHANGELOG.md
#   2. git add 所有非敏感文件
#   3. git commit
#   4. git push origin main
#
# 不会复制/上传：.env（含密钥）、uploads/（原始PDF）、db/（数据库）、__pycache__/

set -euo pipefail

# ── 参数 ─────────────────────────────────────────────────────────────────────
MSG="${1:-}"
if [[ -z "$MSG" ]]; then
  echo "用法: ./backup.sh \"本次修改说明\""
  echo "例:   ./backup.sh \"修复 pdf→docx 中文乱码问题\""
  exit 1
fi

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
DATE="$(date +%Y-%m-%d)"
DATETIME="$(date '+%Y-%m-%d %H:%M:%S')"

cd "$REPO_DIR"

# ── 1. 追加 CHANGELOG ────────────────────────────────────────────────────────
echo ""
echo ">>> [1/4] 追加变更记录到 CHANGELOG.md ..."

# 在第一个 --- 分隔符之前插入新记录
CHANGELOG_ENTRY="
## [$DATE] $MSG

**变更类型**：修改

**变更时间**：$DATETIME

**变更内容**：
- $MSG

**影响范围**：见 git diff

---"

# Prepend after the header line (first line)
HEADER=$(head -3 CHANGELOG.md)
REST=$(tail -n +4 CHANGELOG.md)
{
  echo "$HEADER"
  echo "$CHANGELOG_ENTRY"
  echo "$REST"
} > CHANGELOG.tmp && mv CHANGELOG.tmp CHANGELOG.md

echo "    CHANGELOG.md 已更新"

# ── 2. Git add ───────────────────────────────────────────────────────────────
echo ""
echo ">>> [2/4] 暂存文件 ..."

# Stage everything except secrets and large files
git add \
  main.py \
  requirements.txt \
  README.md \
  CHANGELOG.md \
  DOCS.md \
  backup.sh \
  .env.example \
  .gitignore \
  db/init.sql \
  src/ \
  prompts/ \
  2>/dev/null || true

# Show what's staged
git status --short

# ── 3. Git commit ─────────────────────────────────────────────────────────────
echo ""
echo ">>> [3/4] 提交 ..."

git commit -m "$(cat <<EOF
backup: $MSG [$DATE]

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"

# ── 4. Git push ───────────────────────────────────────────────────────────────
echo ""
echo ">>> [4/4] 推送到 GitHub ..."
git push origin main

echo ""
echo "✓ 备份完成：$MSG"
echo "  仓库：$(git remote get-url origin | sed 's|://[^@]*@|://|')"
echo "  分支：$(git branch --show-current)"
echo "  提交：$(git log -1 --format='%h %s')"
