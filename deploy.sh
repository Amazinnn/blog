#!/usr/bin/env bash
# 一键发布：重新构建 + 提交 + 推送到 GitHub
#
# 用法：
#     ./deploy.sh "这次更新了什么"
#
# 做三件事：
#   1. 跑 build.py 重新生成 docs/
#   2. git add 所有改动并提交
#   3. 推送到 GitHub → Pages 自动更新（约 1 分钟）
set -euo pipefail

cd "$(dirname "$0")"

MSG="${1:-更新博客}"

echo "▶ 构建..."
python3 build.py

echo
echo "▶ 提交..."
git add -A
if git diff --cached --quiet; then
  echo "  （没有改动，跳过提交）"
else
  git commit -q -m "$MSG"
  echo "  ✓ $MSG"
fi

echo
echo "▶ 推送..."
git push -q origin main
echo "  ✓ 已推送"
echo
echo "✅ 完成。约 1 分钟后生效："
echo "   https://amazinnn.github.io/blog/"
