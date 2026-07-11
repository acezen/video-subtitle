# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Claude Code Skill，为视频生成中文字幕。支持从 YouTube 下载视频和用户上传字幕。流水线:yt-dlp 下载视频和字幕 → 如有用户上传字幕则 AI 审核 → 如无字幕则 Whisper 转录 → AI 审核 + 人工确认 → AI 翻译术语方案 + 人工确认 → AI 翻译生成中文 SRT。

## 架构

```
video-subtitle/
  SKILL.md                    # Skill 定义与完整流水线指令
  scripts/
    download.sh               # YouTube 视频+字幕下载（优先 1080p mp4）
    transcribe.sh             # Whisper small 语音识别 → .whisper.srt
    mimo_asr.py               # mimo-v2.5-asr API（暂未启用）
```

- `SKILL.md` 定义完整流水线：下载视频+字幕 → 字幕审核或 Whisper 转录 → AI 审核识别错误 → 人工确认 → AI 术语方案 → 人工确认 → AI 翻译
- `download.sh` 通过 yt-dlp 下载 YouTube 视频和用户上传字幕，优先 1080p，输出 mp4
- `transcribe.sh` 使用 Whisper small 模型进行语音识别，输出 `.whisper.srt`
- 审核和翻译步骤由 AI 模型完成，需人工确认后继续

## 外部依赖

- `ffmpeg` — 音视频处理
- `yt-dlp` — YouTube 视频和字幕下载
- `whisper`（openai-whisper）— 语音识别（当视频无字幕时需要）

## 常用命令

```bash
# 步骤 0: 下载 YouTube 视频和字幕（可选，优先 1080p mp4）
bash scripts/download.sh "<youtube_url>" "<output_dir>" "<source_lang>"

# 步骤 1（无字幕时）: 提取音频并转录为 Whisper 原始字幕
bash scripts/transcribe.sh "<video_path>" "<source_lang>"
```

步骤 1（AI 审核 + 人工确认）：
- 有下载字幕：AI 读取 `.downloaded.srt`，列出疑似错误交用户确认，确认后生成 `.orig.srt`
- 无下载字幕：AI 读取 `.whisper.srt`，列出疑似错误交用户确认，确认后生成 `.orig.srt`

步骤 2（术语方案 + 人工确认）：AI 整理专业术语翻译方案交用户确认。

步骤 3（AI 翻译）：AI 读取 `.orig.srt`，按确认的术语表翻译，输出 `.zh.srt`。

## 关键细节

- `download.sh` 仅下载用户上传字幕，保存为 `.downloaded.srt`；无用户字幕时由 Whisper 转录
- 下载的字幕和 Whisper 输出都需经人工审核确认后才生成 `.orig.srt`
- `transcribe.sh` 使用 Whisper `small` 模型，速度快且精度足够
- 翻译前需先提交术语方案给用户确认，确保专业术语翻译准确
- `mimo_asr.py` 暂未启用，保留备用
