#!/usr/bin/env bash
set -euo pipefail

URL="$1"
OUTPUT_DIR="${2:-.}"
SRC_LANG="${3:-en}"

if [ -z "$URL" ]; then
  echo "错误: 请提供 YouTube 视频 URL" >&2
  exit 1
fi

if ! command -v yt-dlp &>/dev/null; then
  echo "错误: 未找到 yt-dlp，请先安装: brew install yt-dlp" >&2
  exit 1
fi

echo ">>> [1/2] 下载 YouTube 视频 (优先 1080p)..."
yt-dlp \
  -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
  --no-playlist \
  "$URL"

# 获取下载后的视频文件路径
VIDEO_PATH=$(yt-dlp --print filename \
  -f "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=1080]+bestaudio/best[height<=1080]/best" \
  --merge-output-format mp4 \
  -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
  --no-playlist \
  "$URL" 2>/dev/null || true)

echo ">>> 视频已下载 -> $VIDEO_PATH"

# 获取视频文件名（不含扩展名）
VIDEO_DIR="$(dirname "$VIDEO_PATH")"
VIDEO_BASE="$(basename "${VIDEO_PATH%.*}")"
SUB_FOUND=""

echo ">>> [2/2] 尝试下载字幕 (语言: $SRC_LANG)..."

# 优先下载用户上传的字幕
echo "    尝试用户上传字幕..."
if yt-dlp \
  --write-sub \
  --sub-langs "$SRC_LANG" \
  --sub-format srt \
  --convert-subs srt \
  -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
  --no-playlist \
  "$URL" 2>/dev/null; then
  # 检查是否下载到了字幕文件
  SUB_FILE="$OUTPUT_DIR/$VIDEO_BASE.$SRC_LANG.srt"
  if [ -f "$SUB_FILE" ]; then
    mv "$SUB_FILE" "$OUTPUT_DIR/$VIDEO_BASE.downloaded.srt"
    SUB_FOUND="user"
    echo "    ✓ 用户上传字幕已下载"
  fi
fi

# 如果没有用户上传字幕，尝试自动生成字幕
if [ -z "$SUB_FOUND" ]; then
  echo "    未找到用户上传字幕，尝试自动生成字幕..."
  if yt-dlp \
    --write-auto-sub \
    --sub-langs "$SRC_LANG" \
    --sub-format srt \
    --convert-subs srt \
    -o "$OUTPUT_DIR/%(title)s.%(ext)s" \
    --no-playlist \
    "$URL" 2>/dev/null; then
    SUB_FILE="$OUTPUT_DIR/$VIDEO_BASE.$SRC_LANG.srt"
    if [ -f "$SUB_FILE" ]; then
      mv "$SUB_FILE" "$OUTPUT_DIR/$VIDEO_BASE.downloaded.srt"
      SUB_FOUND="auto"
      echo "    ✓ 自动生成字幕已下载"
    fi
  fi
fi

# 输出结果
if [ -n "$SUB_FOUND" ]; then
  echo ">>> 完成: 视频 -> $VIDEO_PATH"
  echo ">>> 完成: 字幕 -> $OUTPUT_DIR/$VIDEO_BASE.downloaded.srt ($SUB_FOUND)"
  echo ">>> 下一步:请由 AI 审核字幕质量，人工确认后生成 .orig.srt"
else
  echo ">>> 完成: 视频 -> $VIDEO_PATH"
  echo ">>> 未找到字幕，需要使用 Whisper 语音识别"
fi
