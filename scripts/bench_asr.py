"""ASR 基准：用 AliMeeting near 集测 faster-whisper 的 CER 与 RTF。

复用线上 LocalASR.transcribe，测的就是生产路径。
- CER（字错误率）= 编辑距离 / 参考字数（中文按字），需 TextGrid 参考。
- RTF（实时率）= 转写耗时 / 音频时长，<1 即快过实时。

用法：
    uv run python scripts/bench_asr.py --limit 3 --clip-seconds 60 --detail
    uv run python scripts/bench_asr.py --model small --device cpu
"""
import argparse
import re
import sys
import time
import unicodedata
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from app.core.config import get_settings
from app.services.asr.local_asr import LocalASR

settings = get_settings()
DEFAULT_NEAR = r"D:\开源数据集kaggel\audio\Eval_Ali\Eval_Ali_near"
DEFAULT_FAR = r"D:\开源数据集kaggel\audio\Eval_Ali\Eval_Ali_far"

try:
    from opencc import OpenCC
    _cc = OpenCC("t2s")
    def to_simplified(t: str) -> str:
        return _cc.convert(t)
except ImportError:
    _cc = None
    def to_simplified(t: str) -> str:
        return t


def parse_textgrid(path: Path, clip: float | None, sort_by_time: bool = False) -> str:
    content = path.read_text(encoding="utf-8", errors="replace")
    items = []
    for block in re.split(r"intervals \[\d+\]:", content)[1:]:
        tm = re.search(r'text\s*=\s*"(.*)"', block)
        if not tm:
            continue
        xm = re.search(r"xmin\s*=\s*([\d.]+)", block)
        xmin = float(xm.group(1)) if xm else 0.0
        if clip and xmin >= clip:
            continue
        items.append((xmin, tm.group(1)))
    if sort_by_time:
        items.sort(key=lambda x: x[0])
    return "".join(t for _, t in items)


def read_audio_clip(path: Path, clip: float | None):
    """用 faster-whisper 的 decode_audio（PyAV 后端）解码：
    支持 WAVE_FORMAT_EXTENSIBLE(far 8通道) 与标准 PCM(near)，统一转 16k mono float32"""
    from faster_whisper.audio import decode_audio
    audio = decode_audio(str(path), 16000)
    if clip:
        audio = audio[: int(16000 * clip)]
    return np.asarray(audio, dtype=np.float32), len(audio) / 16000

def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    return re.sub(r"[^\w]", "", text).lower()


def edit_distance(a, b) -> int:
    m, n = len(a), len(b)
    if m == 0:
        return n
    if n == 0:
        return m
    prev = list(range(n + 1))
    for i in range(1, m + 1):
        cur = [i] + [0] * n
        ai = a[i - 1]
        for j in range(1, n + 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ai != b[j - 1]))
        prev = cur
    return prev[n]


def cer(ref: str, hyp: str):
    r = list(normalize(to_simplified(ref)))
    h = list(normalize(to_simplified(hyp)))
    if not r:
        return 0.0, 0, 0
    d = edit_distance(r, h)
    return d / len(r), d, len(r)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--near-dir", default=DEFAULT_NEAR)
    p.add_argument("--far-dir", default=DEFAULT_FAR)
    p.add_argument("--far", action="store_true", help="测远场 far（8通道混合 + 多tier标注合并）")
    p.add_argument("--limit", type=int, default=5)
    p.add_argument("--clip-seconds", type=float, default=60.0)
    p.add_argument("--model", default=None)
    p.add_argument("--device", default=None)
    p.add_argument("--detail", action="store_true")
    p.add_argument("--debug-text", action="store_true")
    p.add_argument("--min-ref", type=int, default=20, help="参考字数低于此值的文件视为语音过少，跳过")
    args = p.parse_args()

    if args.model:
        settings.WHISPER_MODEL = args.model
    if args.device:
        settings.WHISPER_DEVICE = args.device
    LocalASR._model = None

    base = Path(args.far_dir if args.far else args.near_dir)
    audio_dir, tg_dir = base / "audio_dir", base / "textgrid_dir"
    wavs = sorted(audio_dir.glob("*.wav"))
    if args.limit:
        wavs = wavs[:args.limit]

    asr = LocalASR()
    asr.transcribe(np.zeros(16000, dtype=np.float32), 16000)  # 预热：排除模型载入，避免污染 RTF
    tot_dist = tot_ref = 0
    tot_proc = tot_dur = 0.0
    n_ok = 0
    for wav in wavs:
        if args.far:
            m = re.match(r"(R\d+_M\d+)", wav.stem)
            tg = tg_dir / (m.group(1) + ".TextGrid") if m else tg_dir / (wav.stem + ".TextGrid")
        else:
            tg = tg_dir / (wav.stem + ".TextGrid")
        if not tg.exists():
            print(f"跳过（无标注）: {wav.name}")
            continue
        audio, dur = read_audio_clip(wav, args.clip_seconds)
        ref = parse_textgrid(tg, args.clip_seconds, sort_by_time=args.far)
        t0 = time.time()
        segs = asr.transcribe(audio, 16000)
        proc = time.time() - t0
        hyp = "".join(s["text"] for s in segs)
        c, dist, reflen = cer(ref, hyp)
        hyp_len = len(normalize(to_simplified(hyp)))
        if reflen < args.min_ref or hyp_len < 5:
            if args.detail:
                print(f"  [跳过·语音过少] {wav.name}  ref字={reflen}  hyp字={hyp_len}")
            continue
        rtf = proc / dur if dur else 0.0
        tot_dist += dist
        tot_ref += reflen
        tot_proc += proc
        tot_dur += dur
        n_ok += 1
        if args.detail:
            print(f"  {wav.name}  CER={c:.3f}  RTF={rtf:.3f}  dur={dur:.1f}s proc={proc:.1f}s ref字={reflen}")
        if args.debug_text and n_ok == 1:
            print(f"\n  [DEBUG 首文件文本对比] {wav.name}")
            print(f"  REF(原文): {ref[:120]}")
            print(f"  HYP(原文): {hyp[:120]}")
            print(f"  HYP(转简): {to_simplified(hyp)[:120]}")
            print(f"  归一REF : {normalize(to_simplified(ref))[:120]}")
            print(f"  归一HYP : {normalize(to_simplified(hyp))[:120]}\n")

    print()
    print(f"=== ASR 基准（{'far 远场' if args.far else 'near 近场'}, {n_ok} 文件, "
          f"model={settings.WHISPER_MODEL}, device={settings.WHISPER_DEVICE}, clip={args.clip_seconds}s）===")
    print(f"  总 CER（加权）: {tot_dist / tot_ref if tot_ref else 0:.4f}  ({tot_dist}/{tot_ref} 字)")
    print(f"  平均 RTF     : {tot_proc / tot_dur if tot_dur else 0:.4f}  (处理 {tot_proc:.1f}s / 音频 {tot_dur:.1f}s)")
    if _cc is None:
        print("  ⚠ 未装 opencc：whisper 若输出繁体未转简体，CER 会虚高。装：uv add opencc-python-reimplemented")


if __name__ == "__main__":
    main()