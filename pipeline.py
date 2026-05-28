"""
语音转文字后端流水线 v0.0.2
用法: py -3.12 pipeline.py <input> [--output-dir DIR] [--lang auto|zh|en|ja]
                       [--format txt|srt] [--diarize] [--merge] [--punctuate]
输出 JSON 进度到 stdout（每行一条），调试信息到 stderr
"""
import sys, os, json, time, subprocess, tempfile, logging
from datetime import datetime

import torch

logging.basicConfig(level=logging.WARNING, format="[pipeline] %(levelname)s: %(message)s",
                    stream=sys.stderr)
log = logging.getLogger(__name__)

TOOL_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG = os.path.join(TOOL_DIR, "ffmpeg.exe")

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

def progress(msg, pct=None):
    out = {"status": msg}
    if pct is not None:
        out["progress"] = pct
    print(json.dumps(out), flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="音频/视频文件路径")
    parser.add_argument("--output-dir", default=None, help="输出目录")
    parser.add_argument("--lang", default="auto", choices=["auto","zh","en","ja"])
    parser.add_argument("--format", default="txt", choices=["txt","srt"])
    parser.add_argument("--diarize", action="store_true")
    parser.add_argument("--merge", action="store_true")
    parser.add_argument("--punctuate", action="store_true")
    args = parser.parse_args()

    input_path = args.input
    if not os.path.exists(input_path):
        print(json.dumps({"status": "error", "message": f"文件不存在: {input_path}"}))
        return 1

    # 输出目录
    if args.output_dir:
        out_dir = args.output_dir
        os.makedirs(out_dir, exist_ok=True)
    else:
        out_dir = os.path.dirname(os.path.abspath(input_path))
    base_name = os.path.splitext(os.path.basename(input_path))[0]

    # 提取音频（如果是视频）
    audio_path = input_path
    ext = os.path.splitext(input_path)[1].lower()
    if ext in (".mp4", ".avi", ".mov", ".mkv", ".wmv", ".webm", ".flv", ".ts"):
        progress("提取音频...", 5)
        audio_path = os.path.join(out_dir, base_name + "_audio.wav")
        cmd = [FFMPEG, "-y", "-i", input_path, "-vn", "-ar", "16000", "-ac", "1", audio_path]
        try:
            subprocess.run(cmd, capture_output=True, check=True)
        except subprocess.CalledProcessError as e:
            progress("提取音频失败，文件可能已损坏或格式不支持", 0)
            print(json.dumps({"status": "error", "message": f"ffmpeg音频提取失败: {e.stderr.decode(errors='replace')[:200]}"}))
            return 1
        except FileNotFoundError:
            progress("ffmpeg.exe 未找到", 0)
            print(json.dumps({"status": "error", "message": "ffmpeg.exe not found. Place it in the tool directory."}))
            return 1

    # 语言映射
    lang_map = {"auto": None, "zh": "zh", "en": "en", "ja": "ja"}

    # Step 1: 转录
    progress("加载转录模型...", 5)
    from faster_whisper import WhisperModel

    # 检查 CUDA
    device = "cuda" if torch.cuda.is_available() else "cpu"
    compute = "auto"

    model = WhisperModel("medium", device=device, compute_type=compute,
                         download_root=os.path.join(os.path.expanduser("~"), ".cache", "faster-whisper"))

    progress(f"模型已加载 (device={device})", 20)

    # 实际转写
    progress("转写中...", 22)
    segments_raw, info = model.transcribe(
        audio_path,
        beam_size=5,
        language=lang_map[args.lang],
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
    )

    # 收集结果
    segments = []
    total_dur = info.duration
    for seg in segments_raw:
        segments.append({
            "start": seg.start, "end": seg.end, "text": seg.text.strip()
        })
        pct = 22 + int(min(seg.start / total_dur * 33, 33))
        progress(f"转写中... {len(segments)}段", pct)

    # 标点恢复（仅中文）
    if args.punctuate:
        detected_lang = lang_map[args.lang] or info.language
        if detected_lang and detected_lang.startswith("zh"):
            progress("加载标点模型...", 50)
            from transformers import pipeline
            
            punct_pipe = pipeline(
                "token-classification",
                model="p208p2002/zh-wiki-punctuation-restore",
                aggregation_strategy="simple",
            )
            for seg in segments:
                if not seg["text"]:
                    continue
                try:
                    results = punct_pipe(seg["text"])
                except Exception:
                    log.warning("标点模型推断失败，跳过该段")
                    continue
                chars = list(seg["text"])
                offset = 0
                for r in sorted(results, key=lambda x: x["end"], reverse=True):
                    tag = r["entity_group"]
                    pos = r["end"]
                    if tag not in ("。", "，", "？", "！", "；", "、") or pos > len(chars):
                        continue
                    # 验证 BERT tokenizer 位置映射正确
                    expected = seg["text"][r["start"]:r["end"]]
                    if expected != r.get("word", expected):
                        log.debug("标点位置映射不一致，跳过: %s", r)
                        continue
                    chars.insert(pos + offset, tag)
                    offset += 1
                seg["text"] = "".join(chars)
            progress("标点恢复完成", 53)
        else:
            progress("非中文，跳过标点恢复", 53)

    # Step 2: 说话人分离
    sf_audio_path = audio_path
    if args.diarize:
        progress("加载说话人识别模型...", 55)
        import soundfile as sf

        # soundfile 只支持 WAV/FLAC，非 WAV 需先转换
        sf_audio_path = audio_path
        if not audio_path.lower().endswith((".wav", ".flac")):
            sf_audio_path = os.path.join(out_dir, base_name + "_diarize.wav")
            try:
                subprocess.run([FFMPEG, "-y", "-i", audio_path, "-ar", "16000", "-ac", "1", sf_audio_path],
                               capture_output=True, check=True)
            except subprocess.CalledProcessError as e:
                progress("音频转换失败", 0)
                print(json.dumps({"status": "error", "message": f"音频转换失败: {e.stderr.decode(errors='replace')[:200]}"}))
                return 1

        samples, sr = sf.read(sf_audio_path, dtype="float32")
        if samples.ndim > 1:
            samples = samples.mean(axis=1)
        waveform = torch.from_numpy(samples).unsqueeze(0)

        from pyannote.audio import Pipeline
        token = os.environ.get("HF_TOKEN")
        if not token:
            progress("错误: 未设置 HF_TOKEN 环境变量，请先运行 setup.bat", 0)
            print(json.dumps({"status": "error", "message": "HF_TOKEN not set. Run setup.bat first."}))
            return 1
        pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", token=token)
        pipeline.to(torch.device("cpu"))  # CPU 模式避免 cuDNN 兼容问题

        progress("识别说话人...", 65)
        result = pipeline({"waveform": waveform, "sample_rate": sr})
        ann = result.speaker_diarization

        # 匹配说话人
        for seg in segments:
            speakers = {}
            mid = (seg["start"] + seg["end"]) / 2
            dur = seg["end"] - seg["start"]
            margin = max(dur / 2, 1.0)
            for turn, _, spk in ann.itertracks(yield_label=True):
                if turn.start - margin <= mid <= turn.end + margin:
                    overlap = min(turn.end, seg["end"]) - max(turn.start, seg["start"])
                    if overlap > 0:
                        speakers[spk] = speakers.get(spk, 0) + overlap
            seg["speaker"] = max(speakers, key=speakers.get) if speakers else "UNKNOWN"
        progress("说话人识别完成", 80)
    else:
        for seg in segments:
            seg["speaker"] = ""

    # Step 3: 输出
    progress("生成文件...", 90)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    if args.format == "srt":
        output_path = os.path.join(out_dir, f"{base_name}_{ts}.srt")
        with open(output_path, "w", encoding="utf-8") as f:
            idx = 1
            for seg in segments:
                start_ts = f"{int(seg['start']//3600):02}:{int((seg['start']%3600)//60):02}:{int(seg['start']%60):02},{int((seg['start']%1)*1000):03}"
                end_ts = f"{int(seg['end']//3600):02}:{int((seg['end']%3600)//60):02}:{int(seg['end']%60):02},{int((seg['end']%1)*1000):03}"
                prefix = f"[{seg['speaker']}] " if seg['speaker'] else ""
                f.write(f"{idx}\n{start_ts} --> {end_ts}\n{prefix}{seg['text']}\n\n")
                idx += 1
    else:
        output_path = os.path.join(out_dir, f"{base_name}_转写_{ts}.txt")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"文件：{os.path.basename(input_path)}\n")
            f.write(f"转写模型：Faster-Whisper medium\n")
            if args.diarize:
                f.write(f"说话人：pyannote 3.1\n")
            f.write("=" * 60 + "\n\n")

            if args.diarize and args.merge:
                # 合并同说话人连续段落
                merged_blocks = []
                for seg in segments:
                    if merged_blocks and merged_blocks[-1]["speaker"] == seg["speaker"]:
                        merged_blocks[-1]["text"] += " " + seg["text"]
                        merged_blocks[-1]["end"] = seg["end"]
                    else:
                        merged_blocks.append(seg.copy())
                
                for seg in merged_blocks:
                    ts = f"{int(seg['start']//60):02}:{int(seg['start']%60):02}"
                    spk = seg.get("speaker", "")
                    f.write(f"{spk} {ts}\n{seg['text']}\n\n")
            else:
                for seg in segments:
                    ts = f"[{int(seg['start']//60):02}:{int(seg['start']%60):02} - {int(seg['end']//60):02}:{int(seg['end']%60):02}]"
                    if seg.get("speaker"):
                        f.write(f"{seg['speaker']} {ts}\n{seg['text']}\n\n")
                    else:
                        f.write(f"{ts}\n{seg['text']}\n\n")

    # 清理临时文件
    if audio_path != input_path and os.path.exists(audio_path):
        os.remove(audio_path)
    if args.diarize and sf_audio_path != audio_path and os.path.exists(sf_audio_path):
        os.remove(sf_audio_path)

    progress("完成", 100)
    print(json.dumps({"status": "done", "output": output_path}))


if __name__ == "__main__":
    sys.exit(main() or 0)
