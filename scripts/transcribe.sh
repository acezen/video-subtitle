#!/usr/bin/env bash
set -euo pipefail

VIDEO="$1"
SRC_LANG="${2:-auto}"

if [ ! -f "$VIDEO" ]; then
  echo "错误:找不到视频文件 $VIDEO" >&2
  exit 1
fi

DIR="$(dirname "$VIDEO")"
BASE="$(basename "${VIDEO%.*}")"

AUDIO="$DIR/$BASE.wav"

echo ">>> [1/2] 提取音频..."
ffmpeg -y -i "$VIDEO" -vn -acodec pcm_s16le -ar 16000 -ac 1 "$AUDIO"

echo ">>> [2/2] Whisper 语音识别 (语言: $SRC_LANG)..."
LANG_ARG=""
if [ "$SRC_LANG" != "auto" ]; then
  LANG_ARG="--language $SRC_LANG"
fi

whisper "$AUDIO" \
  --model small \
  $LANG_ARG \
  --task transcribe \
  --output_format srt \
  --output_dir "$DIR"

mv "$DIR/$BASE.srt" "$DIR/$BASE.whisper.srt"

rm -f "$AUDIO"

echo ">>> 完成:Whisper 原始字幕已生成 -> $DIR/$BASE.whisper.srt"
echo ">>> 下一步:请由 AI 审核识别错误，人工确认后生成 .orig.srt"
