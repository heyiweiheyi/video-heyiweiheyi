#!/usr/bin/env python3
"""Apply '电影感若隐若现' (Double-Exposure Ghost Overlay: 0% -> 50% -> 0%) transition."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

FOUNDATIONS_SCRIPTS = Path(__file__).resolve().parents[3] / "foundations" / "scripts"
if str(FOUNDATIONS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FOUNDATIONS_SCRIPTS))

from ffmpeg_utils import get_ffmpeg_exe, image_to_ken_burns, normalize_clip, probe_media_info

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def apply_ghost_double_exposure(
    base_clip: str | Path,
    overlay_media: str | Path,
    output_path: str | Path,
    start: float = 0.5,
    duration: float = 3.0,
    peak_opacity: float = 0.50,
    aspect: str = "16:9",
    fps: int = 30,
    fit_mode: str = "cover",
    crf: int = 18,
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    peak = max(0.05, min(0.95, peak_opacity))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        base_norm = tmp / "base_norm.mp4"
        normalize_clip(base_clip, base_norm, aspect=aspect, fps=fps, fit_mode=fit_mode, crf=crf)
        base_dur = probe_media_info(base_norm)["duration_sec"] or 4.0

        ov_start = max(0.0, min(start, max(0.0, base_dur - 0.6)))
        ov_dur = max(0.6, min(duration, base_dur - ov_start))
        half = ov_dur * 0.5

        ov_path = Path(overlay_media)
        ov_norm = tmp / "overlay_norm.mp4"
        if ov_path.suffix.lower() in IMAGE_EXTS:
            image_to_ken_burns(
                ov_path,
                ov_norm,
                duration=ov_dur + 0.2,
                aspect=aspect,
                fps=fps,
                zoom_start=1.0,
                zoom_end=1.06,
                fit_mode=fit_mode,
                crf=crf,
            )
        else:
            normalize_clip(ov_path, ov_norm, aspect=aspect, fps=fps, fit_mode=fit_mode, crf=crf)

        ov_end = ov_start + ov_dur
        filter_complex = (
            f"[1:v]trim=0:{ov_dur:.3f},setpts=PTS-STARTPTS,format=rgba,"
            f"fade=t=in:st=0:d={half:.3f}:alpha=1,"
            f"fade=t=out:st={half:.3f}:d={half:.3f}:alpha=1,"
            f"colorchannelmixer=aa={peak:.3f},"
            f"setpts=PTS+{ov_start:.3f}/TB[ov];"
            f"[0:v][ov]overlay=0:0:eof_action=pass:enable='between(t,{ov_start:.3f},{ov_end:.3f})',"
            f"format=yuv420p[vout]"
        )

        cmd = [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(base_norm),
            "-stream_loop",
            "-1",
            "-i",
            str(ov_norm),
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "0:a",
            "-t",
            f"{base_dur:.3f}",
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
            raise RuntimeError(f"电影感若隐若现渲染失败: {res.stderr}")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="施加「电影感若隐若现」双重曝光浮影效果")
    parser.add_argument("--base", required=True, help="底层主画面视频路径")
    parser.add_argument("--overlay", required=True, help="上层浮影视频或图片路径")
    parser.add_argument("--output", required=True, help="输出视频路径")
    parser.add_argument("--start", type=float, default=0.5, help="浮影开始显现时间（秒，默认 0.5）")
    parser.add_argument("--duration", type=float, default=3.0, help="浮影完整显隐时长（秒，默认 3.0）")
    parser.add_argument(
        "--peak-opacity",
        type=float,
        default=0.50,
        help="浮影中点峰值不透明度（0.05–0.95，默认 0.50 对应剪映 50%）",
    )
    parser.add_argument("--aspect", default="16:9", help="统一画幅 (16:9 / 9:16 / 1:1)")
    parser.add_argument("--fps", type=int, default=30, help="统一帧率 (默认 30)")
    parser.add_argument("--fit-mode", choices=["cover", "blur_fit"], default="cover", help="画幅适配方式")
    args = parser.parse_args()

    out = apply_ghost_double_exposure(
        base_clip=args.base,
        overlay_media=args.overlay,
        output_path=args.output,
        start=args.start,
        duration=args.duration,
        peak_opacity=args.peak_opacity,
        aspect=args.aspect,
        fps=args.fps,
        fit_mode=args.fit_mode,
    )
    print(f"电影感若隐若现已生成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
