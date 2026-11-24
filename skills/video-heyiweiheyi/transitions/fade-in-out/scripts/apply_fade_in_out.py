#!/usr/bin/env python3
"""Apply '逐渐显现/消失' (Fade-In / Fade-Out) opacity keyframe transition via FFmpeg."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

FOUNDATIONS_SCRIPTS = Path(__file__).resolve().parents[3] / "foundations" / "scripts"
if str(FOUNDATIONS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FOUNDATIONS_SCRIPTS))

from ffmpeg_utils import get_ffmpeg_exe, probe_media_info


def apply_fade_in_out(
    input_path: str | Path,
    output_path: str | Path,
    fade_in: float = 1.5,
    fade_out: float = 1.5,
    audio_fade: bool = True,
    crf: int = 18,
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    info = probe_media_info(input_path)
    dur = info["duration_sec"] or 1.0
    fin = max(0.0, min(fade_in, dur * 0.45))
    fout = max(0.0, min(fade_out, dur * 0.45))

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    vf_parts: list[str] = []
    af_parts: list[str] = []
    if fin > 0:
        vf_parts.append(f"fade=t=in:st=0:d={fin:.3f}")
        if audio_fade and info["has_audio"]:
            af_parts.append(f"afade=t=in:st=0:d={fin:.3f}")
    if fout > 0:
        st_out = max(0.0, dur - fout)
        vf_parts.append(f"fade=t=out:st={st_out:.3f}:d={fout:.3f}")
        if audio_fade and info["has_audio"]:
            af_parts.append(f"afade=t=out:st={st_out:.3f}:d={fout:.3f}")

    vf_parts.append("format=yuv420p")
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-vf",
        ",".join(vf_parts),
    ]
    if af_parts:
        cmd += ["-af", ",".join(af_parts)]

    cmd += [
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
    ]
    if info["has_audio"]:
        cmd += ["-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"]
    cmd += ["-movflags", "+faststart", str(out)]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"逐渐显现/消失渲染失败: {res.stderr}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="施加「逐渐显现/消失」转场效果")
    parser.add_argument("--input", required=True, help="输入视频路径")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument("--fade-in", type=float, default=1.5, help="开头渐显时长（秒，0 表示不淡入）")
    parser.add_argument("--fade-out", type=float, default=1.5, help="结尾渐隐时长（秒，0 表示不淡出）")
    parser.add_argument("--no-audio-fade", action="store_true", help="不同步淡入淡出音频")
    args = parser.parse_args()

    out = apply_fade_in_out(
        input_path=args.input,
        output_path=args.output,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        audio_fade=not args.no_audio_fade,
    )
    print(f"逐渐显现/消失已生成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
