#!/usr/bin/env bash
set -euo pipefail

URL="$1"
OUTPUT_DIR="${2:-.}"

if [ -z "$URL" ]; then
  echo "错误: 请提供 YouTube 视频 URL" >&2
  exit 1
fi

if ! command -v yt-dlp &>/dev/null; then
  echo "错误: 未找到 yt-dlp，请先安装: brew install yt-dlp" >&2
  exit 1
fi

echo ">>> 下载 YouTube 视频 (优先 1080p)..."
yt-dlp \
  -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
  --no-playlist \
  "$URL"

# 获取下载后的文件路径
VIDEO_PATH=$(yt-dlp --print filename \
  -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
  --no-playlist \
  "$URL" 2>/dev/null || true)

echo ">>> 完成: 视频已下载 -> $VIDEO_PATH"
