# video-subtitle

视频转中文字幕的 Claude Code Skill。支持从 YouTube 下载视频，通过 Whisper 语音识别生成原语言字幕，再由 AI 翻译校对成中文。

## 流水线

```
YouTube 链接 ──→ yt-dlp 下载 ──→ ffmpeg 提取音频 ──→ Whisper 识别 ──→ AI 翻译 ──→ 中文 SRT
                                  本地视频 ─────────┘
```

## 前置依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| ffmpeg | 音视频处理 | `brew install ffmpeg` |
| whisper | 语音识别 | `pip install openai-whisper` |
| yt-dlp | YouTube 下载（可选） | `brew install yt-dlp` |

## 使用方式

### 作为 Claude Code Skill

将本仓库放到本地，在 Claude Code 中直接说：

> 帮我把这个视频加上中文字幕：https://www.youtube.com/watch?v=xxx

Claude 会自动执行完整流水线并翻译。

### 手动使用

**步骤 0：下载 YouTube 视频（可选）**

```bash
bash scripts/download.sh "https://www.youtube.com/watch?v=xxx" "./output"
```

**步骤 1：语音识别生成原语言 SRT**

```bash
bash scripts/transcribe.sh "<video_path>" "<source_lang>"
# 例：bash scripts/transcribe.sh video.mp4 en
```

生成 `<video_name>.orig.srt`。

**步骤 2：AI 翻译**

读取 `.orig.srt`，翻译成中文后写入 `.zh.srt`。翻译规则见 `SKILL.md`。

## 支持的语言

Whisper 支持多种语言，常用代号：

| 代号 | 语言 |
|------|------|
| en | 英语 |
| zh | 中文 |
| ja | 日语 |
| ko | 韩语 |
| auto | 自动检测 |

## 项目结构

```
video-subtitle/
├── SKILL.md              # Skill 定义与 AI 翻译规则
├── README.md
└── scripts/
    ├── download.sh       # YouTube 视频下载
    ├── transcribe.sh     # Whisper 语音识别
    └── mimo_asr.py       # mimo-v2.5-asr（备用，暂未启用）
```

## 许可证

MIT
