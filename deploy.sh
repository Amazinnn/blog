#!/usr/bin/env bash
# 一键发布：构建 + 提交 + 推送
#
# 用法：
#     ./deploy.sh "这次更新了什么"
#
# token 从 ~/.hermes/.env 的 GITHUB_TOKEN 读，不写进 git 配置。
set -euo pipefail

cd "$(dirname "$0")"

MSG="${1:-更新博客}"
REPO="github.com/Amazinnn/blog.git"
ENV_FILE="$HOME/.hermes/.env"

# 取 token
TOKEN="$(grep -m1 '^GITHUB_TOKEN=' "$ENV_FILE" 2>/dev/null | cut -d= -f2- || true)"
if [ -z "$TOKEN" ]; then
  echo "❌ 未在 $ENV_FILE 找到 GITHUB_TOKEN" >&2
  exit 1
fi

echo "▶ 构建..."
python3 build.py

echo
echo "▶ 提交..."
git add -A
if git diff --cached --quiet; then
  echo "  （无改动）"
else
  git commit -q -m "$MSG"
  echo "  ✓ $MSG"
fi

echo
echo "▶ 推送..."
git push -q "https://Amazinnn:${TOKEN}@${REPO}" main
echo "  ✓ 已推送"

echo
echo "✅ 完成。约 1 分钟后生效："
echo "   https://amazinnn.github.io/blog/"
