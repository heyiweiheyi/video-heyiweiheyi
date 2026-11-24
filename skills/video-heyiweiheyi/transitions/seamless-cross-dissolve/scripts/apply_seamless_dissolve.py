#!/usr/bin/env python3
"""Apply '无缝衔接转场' (Seamless Cross-Dissolve) between two video clips."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

FOUNDATIONS_SCRIPTS = Path(__file__).resolve().parents[3] / "foundations" / "scripts"
if str(FOUNDATIONS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FOUNDATIONS_SCRIPTS))

from ffmpeg_utils import get_ffmpeg_exe, normalize_clip, probe_media_info


def apply_seamless_dissolve(
    clip_a: str | Path,
    clip_b: str | Path,
    output_path: str | Path,
    duration: float = 1.2,
    aspect: str = "16:9",
    fps: int = 30,
    fit_mode: str = "cover",
    crf: int = 18,
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        na = tmp / "a_norm.mp4"
        nb = tmp / "b_norm.mp4"
        normalize_clip(clip_a, na, aspect=aspect, fps=fps, fit_mode=fit_mode, crf=crf)
        normalize_clip(clip_b, nb, aspect=aspect, fps=fps, fit_mode=fit_mode, crf=crf)

        dur_a = probe_media_info(na)["duration_sec"] or 1.0
        dur_b = probe_media_info(nb)["duration_sec"] or 1.0
        td = max(0.1, min(duration, dur_a * 0.48, dur_b * 0.48))
        offset = max(0.0, dur_a - td)

        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(na),
            "-i",
            str(nb),
            "-filter_complex",
            (
                f"[0:v][1:v]xfade=transition=fade:duration={td:.3f}:offset={offset:.3f}[v];"
                f"[0:a][1:a]acrossfade=d={td:.3f}:c1=tri:c2=tri[a]"
            ),
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            str(crf),
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(out),
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"无缝衔接转场渲染失败: {res.stderr}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="施加「无缝衔接转场」交叉叠化效果")
    parser.add_argument("--clip-a", required=True, help="前段视频路径")
    parser.add_argument("--clip-b", required=True, help="后段视频路径")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument("--duration", type=float, default=1.2, help="叠化重叠时长（秒，默认 1.2）")
    parser.add_argument("--aspect", default="16:9", help="统一画幅 (16:9 / 9:16 / 1:1)")
    parser.add_argument("--fps", type=int, default=30, help="统一帧率 (默认 30)")
    parser.add_argument("--fit-mode", choices=["cover", "blur_fit"], default="cover", help="画幅适配方式")
    args = parser.parse_args()

    out = apply_seamless_dissolve(
        clip_a=args.clip_a,
        clip_b=args.clip_b,
        output_path=args.output,
        duration=args.duration,
        aspect=args.aspect,
        fps=args.fps,
        fit_mode=args.fit_mode,
    )
    print(f"无缝衔接转场已生成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
