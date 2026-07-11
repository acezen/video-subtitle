# video-subtitle

视频转中文字幕的 Claude Code Skill。支持从 YouTube 下载视频和字幕，优先使用官方字幕，无字幕时通过 Whisper 语音识别生成原语言字幕，再由 AI 翻译校对成中文。

## 流水线

```
YouTube 链接 ──→ yt-dlp 下载视频+字幕 ──→ 有字幕？
                  本地视频 ─────────┘         ↓ 是          ↓ 否
                                        AI 审核字幕      Whisper 识别
                                              ↓              ↓
                                        人工确认修正    AI 审核识别错误
                                              ↓              ↓
                                              └──→ .orig.srt ←─┘
                                                        ↓
                                                AI 提出术语翻译方案
                                                        ↓
                                                    人工确认术语
                                                        ↓
                                                AI 翻译 → 中文 .zh.srt
```

## 前置依赖

| 工具 | 用途 | 安装 |
|------|------|------|
| ffmpeg | 音视频处理 | `brew install ffmpeg` |
| yt-dlp | YouTube 视频+字幕下载 | `brew install yt-dlp` |
| whisper | 语音识别（无字幕时） | `pip install openai-whisper` |

## 使用方式

### 作为 Claude Code Skill

将本仓库放到本地，在 Claude Code 中直接说：

> 帮我把这个视频加上中文字幕：https://www.youtube.com/watch?v=xxx

Claude 会自动执行完整流水线并翻译。

### 手动使用

**步骤 0：下载 YouTube 视频和字幕**

```bash
bash scripts/download.sh "https://www.youtube.com/watch?v=xxx" "./output" "en"
```

脚本会优先下载用户上传字幕，其次下载 YouTube 自动生成字幕。
如有字幕，生成 `<video_name>.downloaded.srt`；如无字幕，需使用 Whisper。

**步骤 1（无字幕时）：语音识别生成原语言 SRT**

```bash
bash scripts/transcribe.sh "<video_path>" "<source_lang>"
# 例：bash scripts/transcribe.sh video.mp4 en
```

生成 `<video_name>.whisper.srt`（Whisper 原始输出）。

**步骤 1（有字幕时）/ 步骤 2（无字幕时）：AI 审核 + 人工确认**

AI 分析字幕中的疑似错误（同音字、专有名词等），列出修正建议表，人工确认后生成 `.orig.srt`。

**步骤 2：术语方案 + 人工确认**

AI 整理视频中的专业术语翻译方案，人工确认译法。

**步骤 3：AI 翻译**

读取 `.orig.srt`，按确认的术语表翻译成中文，写入 `.zh.srt`。翻译规则见 `SKILL.md`。

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
├── SKILL.md              # Skill 定义与完整流水线指令
├── README.md
└── scripts/
    ├── download.sh       # YouTube 视频+字幕下载
    ├── transcribe.sh     # Whisper 语音识别
    └── mimo_asr.py       # mimo-v2.5-asr（备用，暂未启用）
```

## 许可证

MIT
