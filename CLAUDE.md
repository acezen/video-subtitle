# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Claude Code Skill，为视频生成中文字幕。支持从 YouTube 下载视频。流水线:yt-dlp 下载视频 → ffmpeg 提取音频 → Whisper 转录 → AI 审核 + 人工确认 → AI 翻译术语方案 + 人工确认 → AI 翻译生成中文 SRT。

## 架构

```
video-subtitle/
  SKILL.md                    # Skill 定义与完整流水线指令
  scripts/
    download.sh               # YouTube 视频下载（优先 1080p mp4）
    transcribe.sh             # Whisper small 语音识别 → .whisper.srt
    mimo_asr.py               # mimo-v2.5-asr API（暂未启用）
```

- `SKILL.md` 定义完整流水线：下载 → 转录 → AI 审核识别错误 → 人工确认 → AI 术语方案 → 人工确认 → AI 翻译
- `download.sh` 通过 yt-dlp 下载 YouTube 视频，优先 1080p，输出 mp4
- `transcribe.sh` 使用 Whisper small 模型进行语音识别，输出 `.whisper.srt`
- 审核和翻译步骤由 AI 模型完成，需人工确认后继续

## 外部依赖

- `ffmpeg` — 音视频处理
- `yt-dlp` — YouTube 视频下载
- `whisper`（openai-whisper）— 语音识别

## 常用命令

```bash
# 步骤 0: 下载 YouTube 视频（可选，优先 1080p mp4）
bash scripts/download.sh "<youtube_url>" "<output_dir>"

# 步骤 1: 提取音频并转录为 Whisper 原始字幕
bash scripts/transcribe.sh "<video_path>" "<source_lang>"
```

步骤 2（AI 审核 + 人工确认）：AI 读取 `.whisper.srt`，列出疑似识别错误交用户确认，确认后生成 `.orig.srt`。

步骤 3（术语方案 + 人工确认）：AI 整理专业术语翻译方案交用户确认。

步骤 4（AI 翻译）：AI 读取 `.orig.srt`，按确认的术语表翻译，输出 `.zh.srt`。

## 关键细节

- `transcribe.sh` 使用 Whisper `small` 模型，速度快且精度足够
- Whisper 输出为 `.whisper.srt`，经人工审核确认后才生成 `.orig.srt`
- 翻译前需先提交术语方案给用户确认，确保专业术语翻译准确
- `mimo_asr.py` 暂未启用，保留备用
