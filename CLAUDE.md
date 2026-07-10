# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

这是一个 Claude Code Skill，为视频生成中文字幕。支持从 YouTube 下载视频。流水线:yt-dlp 下载视频 → ffmpeg 提取音频 → Whisper/mimo 转录原语言 SRT → AI 翻译校对成中文 SRT。

## 架构

```
video-subtitle/
  SKILL.md                    # Skill 定义与 AI 翻译指令
  scripts/
    download.sh               # YouTube 视频下载（优先 1080p mp4）
    transcribe.sh             # Whisper small 语音识别 → .orig.srt
    mimo_asr.py               # mimo-v2.5-asr API（暂未启用）
```

- `SKILL.md` 定义流水线及 AI 翻译校对规则（保持 SRT 结构、结合背景纠正同音字、地道中文表达）
- `download.sh` 通过 yt-dlp 下载 YouTube 视频，优先 1080p，输出 mp4
- `transcribe.sh` 使用 Whisper small 模型进行语音识别
- 翻译步骤由 AI 模型直接完成，无需脚本

## 外部依赖

- `ffmpeg` — 音视频处理
- `yt-dlp` — YouTube 视频下载
- `whisper`（openai-whisper）— 语音识别

## 常用命令

```bash
# 步骤 0: 下载 YouTube 视频（可选，优先 1080p mp4）
bash scripts/download.sh "<youtube_url>" "<output_dir>"

# 步骤 1: 提取音频并转录为原语言 SRT
bash scripts/transcribe.sh "<video_path>" "<source_lang>"
```

步骤 2（翻译校对）由 AI 模型直接读取 `.orig.srt` 并输出 `.zh.srt`，无需脚本。

## 关键细节

- `transcribe.sh` 使用 Whisper `small` 模型，速度快且精度足够
- `mimo_asr.py` 暂未启用，保留备用
- 翻译时应结合用户提供的视频背景信息，纠正 Whisper 的同音字和专有名词错误
