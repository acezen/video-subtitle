#!/usr/bin/env python3
"""调用 mimo-v2.5-asr API 进行语音识别，结合 Whisper 时间戳，输出 SRT 字幕文件。

策略：mimo 负责文本质量，Whisper 负责时间戳。
mimo API 不支持返回时间戳，因此用 Whisper 的 segment 时间轴来对齐 mimo 的文本。
"""

import sys
import os
import re
import base64
import shutil
import subprocess
from pathlib import Path
from openai import OpenAI


def get_audio_duration(audio_path: str) -> float:
    """通过 ffprobe 获取音频时长（秒）。"""
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def extract_audio(video_path: str) -> str:
    """用 ffmpeg 从视频提取 16kHz 单声道 WAV，返回音频路径。"""
    video = Path(video_path)
    audio_path = video.with_suffix(".wav")
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(video), "-vn", "-acodec", "pcm_s16le",
         "-ar", "16000", "-ac", "1", str(audio_path)],
        check=True, capture_output=True
    )
    return str(audio_path)


def call_mimo_asr(audio_path: str, language: str) -> str:
    """调用 mimo-v2.5-asr API，返回识别结果文本。"""
    api_key = os.environ.get("MIMO_API_KEY")
    if not api_key:
        print("错误: 未设置 MIMO_API_KEY 环境变量", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=api_key, base_url="https://token-plan-cn.xiaomimimo.com/v1")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()
    audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

    lang = language if language != "auto" else "auto"

    completion = client.chat.completions.create(
        model="mimo-v2.5-asr",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_audio",
                        "input_audio": {
                            "data": f"data:audio/wav;base64,{audio_base64}"
                        }
                    }
                ]
            }
        ],
        extra_body={
            "asr_options": {
                "language": lang
            }
        }
    )

    return completion.choices[0].message.content


def run_whisper_for_timestamps(audio_path: str, language: str, output_dir: str) -> list[dict]:
    """运行 Whisper 获取带时间戳的 segment 列表。"""
    lang_arg = []
    if language != "auto":
        lang_arg = ["--language", language]

    # 先输出 SRT，再解析
    result = subprocess.run(
        ["whisper", audio_path, "--model", "small"] + lang_arg +
        ["--task", "transcribe", "--output_format", "srt", "--output_dir", output_dir],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"Whisper 警告: {result.stderr}", file=sys.stderr)

    # 读取 Whisper 生成的 SRT
    audio_stem = Path(audio_path).stem
    srt_path = os.path.join(output_dir, f"{audio_stem}.srt")

    if not os.path.exists(srt_path):
        return []

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 解析 SRT 为 segments
    segments = []
    blocks = re.split(r'\n\n+', content.strip())
    for block in blocks:
        lines = block.strip().split('\n')
        if len(lines) >= 3:
            time_match = re.match(
                r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})',
                lines[1]
            )
            if time_match:
                text = ' '.join(lines[2:])
                segments.append({
                    'start': time_match.group(1),
                    'end': time_match.group(2),
                    'text': text
                })

    return segments


def parse_srt_from_response(response_text: str):
    """尝试从响应中解析 SRT 格式的条目。"""
    srt_pattern = re.compile(
        r'(\d+)\s*\n\s*(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})\s*\n(.+?)(?=\n\d+\s*\n|\Z)',
        re.DOTALL
    )
    matches = srt_pattern.findall(response_text)
    if matches:
        return [(m[1], m[2], m[3].strip()) for m in matches]
    return None


def split_sentences(text: str) -> list[str]:
    """将文本按句子拆分，去除重复段落。"""
    text = re.sub(r'<[^>]+>', '', text)
    parts = re.split(r'(?<=[。！？.!?\n])\s*', text)
    sentences = [p.strip() for p in parts if p.strip()]
    return deduplicate_sentences(sentences)


def deduplicate_sentences(sentences: list[str]) -> list[str]:
    """去除重复句子，包括连续重复和非连续的循环重复（如 A-B-A-B 模式）。"""
    if len(sentences) <= 1:
        return sentences

    # 第一步：去除连续重复
    no_consecutive = []
    for s in sentences:
        if not no_consecutive or s != no_consecutive[-1]:
            no_consecutive.append(s)

    if len(no_consecutive) <= 2:
        return no_consecutive

    # 第二步：检测循环重复模式（如 A-B-A-B 或 A-B-C-A-B-C）
    # 从最长可能的周期开始检测
    max_period = len(no_consecutive) // 2
    for period in range(2, max_period + 1):
        # 检查从某个位置开始是否进入循环
        for start in range(len(no_consecutive)):
            remaining = no_consecutive[start:]
            if len(remaining) < period * 2:
                continue
            # 检查是否是完整周期的重复
            pattern = remaining[:period]
            is_repeating = True
            repeat_count = 0
            for i in range(period, len(remaining)):
                if remaining[i] != pattern[i % period]:
                    is_repeating = False
                    break
                if (i + 1) % period == 0:
                    repeat_count += 1
            if is_repeating and repeat_count >= 2:
                # 保留 start 之前的句子 + 第一个周期
                return no_consecutive[:start + period]

    return no_consecutive


def srt_time_to_seconds(srt_time: str) -> float:
    """将 SRT 时间戳 00:01:23,456 转换为秒数。"""
    h, m, rest = srt_time.split(':')
    s, ms = rest.split(',')
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000


def format_timestamp(seconds: float) -> str:
    """将秒数转换为 SRT 时间戳格式 00:00:00,000。"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def align_text_to_whisper_segments(mimo_sentences: list[str], whisper_segments: list[dict],
                                    audio_duration: float) -> list[tuple]:
    """将 mimo 的文本句子对齐到 Whisper 的 segment 时间轴。

    策略：将 Whisper 的所有 segment 拼成连续文本，找到 mimo 每句话在
    Whisper 文本中的位置，从而映射到对应的时间区间。
    """
    if not whisper_segments:
        return estimate_timestamps(mimo_sentences, audio_duration)

    if not mimo_sentences:
        return []

    # 拼接 Whisper 的完整文本（小写、去标点）用于模糊匹配
    def normalize(text):
        return re.sub(r'[^\w\s]', '', text.lower()).split()

    whisper_words = []
    word_times = []  # 每个 word 对应的 (start, end)
    for seg in whisper_segments:
        words = normalize(seg['text'])
        seg_start = srt_time_to_seconds(seg['start'])
        seg_end = srt_time_to_seconds(seg['end'])
        n = len(words)
        if n == 0:
            continue
        # 在 segment 内线性分配每个 word 的时间
        word_dur = (seg_end - seg_start) / n
        for i, w in enumerate(words):
            whisper_words.append(w)
            word_times.append((seg_start + i * word_dur, seg_start + (i + 1) * word_dur))

    if not whisper_words:
        return estimate_timestamps(mimo_sentences, audio_duration)

    # 为每个 mimo 句子找到在 Whisper 文本中的起止 word 位置
    results = []
    search_start = 0  # 搜索起始位置（避免回头匹配）

    for sentence in mimo_sentences:
        sent_words = normalize(sentence)
        if not sent_words:
            continue

        # 在 whisper_words 中查找 sent_words 的最佳匹配位置
        match_pos = _fuzzy_find(whisper_words, sent_words, search_start)
        if match_pos >= 0:
            start_time = word_times[match_pos][0]
            # 结束位置：匹配到的最后一个 word
            end_word_pos = min(match_pos + len(sent_words) - 1, len(word_times) - 1)
            end_time = word_times[end_word_pos][1]
            search_start = match_pos + 1  # 下一句从这个位置之后搜索
        else:
            # 匹配失败，用当前搜索位置的 whisper 时间
            if search_start < len(word_times):
                start_time = word_times[search_start][0]
                end_time = min(start_time + len(sentence) * 0.08, audio_duration)
            else:
                start_time = audio_duration - 1.0
                end_time = audio_duration

        results.append((
            format_timestamp(max(start_time, 0)),
            format_timestamp(min(end_time, audio_duration)),
            sentence
        ))

    # 用 Whisper 未匹配到的 segment 补充缺失内容
    # 从最后一个 mimo 匹配的结束时间之后开始补充
    last_end_time = 0
    if results:
        last_end_str = results[-1][1]
        last_end_time = srt_time_to_seconds(last_end_str)
    remaining = get_remaining_whisper_segments(whisper_segments, last_end_time)
    for seg in remaining:
        results.append((seg['start'], seg['end'], seg['text'].strip()))

    return results


def _fuzzy_find(whisper_words: list[str], sent_words: list[str], start: int) -> int:
    """在 whisper_words 中查找 sent_words 的最佳匹配位置。

    使用滑动窗口，选择匹配词数最多的位置。
    """
    if not sent_words:
        return -1

    best_pos = -1
    best_score = 0
    window = len(sent_words)

    # 只搜索合理范围（避免 O(n*m) 太大）
    search_end = min(start + len(whisper_words) - window + 1, len(whisper_words))

    for i in range(start, search_end):
        score = 0
        for j in range(window):
            if i + j < len(whisper_words) and whisper_words[i + j] == sent_words[j]:
                score += 1
        if score > best_score:
            best_score = score
            best_pos = i
            # 如果完全匹配，直接返回
            if score == window:
                return i

    # 至少匹配一半的词才算有效
    if best_score >= max(1, len(sent_words) * 0.4):
        return best_pos
    return -1


def get_remaining_whisper_segments(whisper_segments: list[dict], last_end_time: float) -> list[dict]:
    """获取 Whisper 中在 mimo 匹配结束时间之后的 segment（补充缺失内容）。"""
    remaining = []
    for seg in whisper_segments:
        seg_start = srt_time_to_seconds(seg['start'])
        if seg_start > last_end_time + 0.5:  # 从 mimo 最后结束时间之后开始
            remaining.append(seg)

    return remaining


def estimate_timestamps(sentences: list[str], total_duration: float) -> list[tuple]:
    """根据文本长度比例估算每句的时间戳（回退方案）。"""
    if not sentences:
        return []

    total_chars = sum(len(s) for s in sentences)
    if total_chars == 0:
        return []

    results = []
    current_time = 0.0
    for s in sentences:
        ratio = len(s) / total_chars
        duration = max(ratio * total_duration, 1.0)
        start = current_time
        end = current_time + duration
        results.append((
            format_timestamp(start),
            format_timestamp(end),
            s
        ))
        current_time = end

    return results


def write_srt(entries: list[tuple], output_path: str):
    """将条目写入 SRT 文件。"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, (start, end, text) in enumerate(entries, 1):
            f.write(f"{i}\n{start} --> {end}\n{text}\n\n")


def main():
    if len(sys.argv) < 3:
        print("用法: python3 mimo_asr.py <video_path> <language>", file=sys.stderr)
        sys.exit(1)

    video_path = sys.argv[1]
    language = sys.argv[2]

    if not os.path.isfile(video_path):
        print(f"错误: 找不到视频文件 {video_path}", file=sys.stderr)
        sys.exit(1)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    video = Path(video_path)
    output_dir = str(video.parent)

    print(">>> [1/4] 提取音频...")
    audio_path = extract_audio(video_path)

    print(">>> [2/4] mimo-v2.5-asr 语音识别...")
    response_text = call_mimo_asr(audio_path, language)

    # 保存 mimo 原始输出
    mimo_raw_path = video.with_suffix(".mimo.txt")
    with open(mimo_raw_path, "w", encoding="utf-8") as f:
        f.write(response_text)
    print(f">>> mimo 原始输出已保存 -> {mimo_raw_path}")

    # 解析响应：如果 mimo 直接返回了 SRT 格式则直接用
    entries = parse_srt_from_response(response_text)

    if entries:
        print(">>> 检测到 SRT 格式响应，直接使用")
    else:
        mimo_sentences = split_sentences(response_text)
        print(f">>> mimo 识别到 {len(mimo_sentences)} 个句子")

        # 运行 Whisper 获取时间戳
        print(">>> [3/4] Whisper 获取时间戳...")
        whisper_segments = run_whisper_for_timestamps(audio_path, language, output_dir)
        print(f">>> Whisper 识别到 {len(whisper_segments)} 个 segment")

        # 保存 Whisper 时间戳文本
        whisper_srt_path = video.with_suffix(".whisper.srt")
        write_srt(
            [(s['start'], s['end'], s['text']) for s in whisper_segments],
            str(whisper_srt_path)
        )
        print(f">>> Whisper 时间戳已保存 -> {whisper_srt_path}")

        # 对齐文本
        duration = get_audio_duration(audio_path)
        entries = align_text_to_whisper_segments(mimo_sentences, whisper_segments, duration)

    # 输出路径
    srt_path = video.with_suffix(".orig.srt")

    print(">>> [4/5] 生成 SRT 字幕...")
    write_srt(entries, str(srt_path))

    # 用 ffsubsync 精细对齐时间戳
    print(">>> [5/5] ffsubsync 精细对齐...")
    synced_path = video.with_suffix(".synced.srt")
    try:
        result = subprocess.run(
            ["ffsubsync", str(video), "-i", str(srt_path), "-o", str(synced_path),
             "--no-fix-framerate"],
            capture_output=True, text=True
        )
        if result.returncode == 0 and synced_path.exists():
            shutil.move(str(synced_path), str(srt_path))
            import re as _re
            offset_match = _re.search(r'offset seconds:\s*([-\d.]+)', result.stderr)
            if offset_match:
                print(f">>> 时间戳已对齐 (偏移: {offset_match.group(1)}s)")
            else:
                print(">>> 时间戳已对齐")
        else:
            print(f"ffsubsync 失败，保留原始时间戳", file=sys.stderr)
    except FileNotFoundError:
        print("ffsubsync 未安装，跳过精细对齐", file=sys.stderr)

    # 清理临时文件
    whisper_srt = os.path.join(output_dir, f"{video.stem}.srt")
    for f in [audio_path, whisper_srt, str(synced_path)]:
        if os.path.exists(f):
            os.remove(f)

    print(f">>> 完成: 原语言字幕已生成 -> {srt_path}")


if __name__ == "__main__":
    main()
