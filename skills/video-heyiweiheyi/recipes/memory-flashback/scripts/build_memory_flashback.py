#!/usr/bin/env python3
"""Build a '回忆快闪' (Memory Flashback) video clip using dual-track half-stride
cross-dissolve (0% -> 100% -> 0% opacity keyframes) + Dynamic Zoom Out animation.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FOUNDATIONS_SCRIPTS = (
    Path(__file__).resolve().parents[3] / "foundations" / "scripts"
)
if str(FOUNDATIONS_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(FOUNDATIONS_SCRIPTS))

from ffmpeg_utils import fit_image_to_canvas, get_ffmpeg_exe, parse_aspect_resolution


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff"}


def _natural_sort_key(p: Path) -> list[int | str]:
    return [int(tok) if tok.isdigit() else tok.lower() for tok in re.split(r"(\d+)", p.name)]


def collect_images(images: list[str] | None, images_dir: str | None) -> list[Path]:
    paths: list[Path] = []
    if images_dir:
        d = Path(images_dir)
        if not d.is_dir():
            raise FileNotFoundError(f"图片目录不存在: {d}")
        for f in sorted(d.iterdir(), key=_natural_sort_key):
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS:
                paths.append(f)
    if images:
        for item in images:
            p = Path(item)
            if not p.is_file():
                raise FileNotFoundError(f"图片文件不存在: {p}")
            paths.append(p)
    if len(paths) < 2:
        raise ValueError(f"回忆快闪至少需要 2 张图片（推荐 8–40 张），当前仅检测到 {len(paths)} 张。")
    return paths


def _crop_zoom_frame(base_img: Image.Image, out_w: int, out_h: int, scale: float) -> np.ndarray:
    """Crop centered region from oversized base image corresponding to zoom scale >= 1.0."""
    bw, bh = base_img.size
    # base_img is prepared at base_scale * (out_w, out_h)
    # To show scale=1.0 -> full frame; scale=1.32 -> zoomed in (smaller crop box)
    crop_w = bw / scale
    crop_h = bh / scale
    x1 = (bw - crop_w) * 0.5
    y1 = (bh - crop_h) * 0.5
    frame = base_img.transform(
        (out_w, out_h),
        Image.Transform.EXTENT,
        (x1, y1, x1 + crop_w, y1 + crop_h),
        resample=Image.Resampling.BILINEAR,
    )
    return np.asarray(frame, dtype=np.float32)


def _render_zoom_out_layer(
    base_img: Image.Image,
    out_w: int,
    out_h: int,
    u: float,
    zoom_start: float,
    motion_blur: bool = True,
) -> np.ndarray:
    """Render Dynamic Zoom Out ('动感缩小') at normalized clip progress u in [0, 1]."""
    u = max(0.0, min(1.0, u))
    ease_rem = (1.0 - u) ** 3
    scale = 1.0 + (zoom_start - 1.0) * ease_rem

    # Subtle 3-tap radial zoom blur during the high-velocity opening burst (u < 0.35)
    if motion_blur and u < 0.35 and zoom_start > 1.05:
        blur_strength = (1.0 - u / 0.35) * 0.032 * (zoom_start - 1.0) / 0.32
        s_hi = min(zoom_start, scale * (1.0 + blur_strength))
        s_lo = max(1.0, scale * (1.0 - blur_strength))
        f0 = _crop_zoom_frame(base_img, out_w, out_h, scale)
        f1 = _crop_zoom_frame(base_img, out_w, out_h, s_hi)
        f2 = _crop_zoom_frame(base_img, out_w, out_h, s_lo)
        return 0.54 * f0 + 0.23 * f1 + 0.23 * f2

    return _crop_zoom_frame(base_img, out_w, out_h, scale)


def _opacity_triangle(u: float) -> float:
    """0.00s -> 0%, 0.50 -> 100%, 1.00 -> 0%."""
    if u <= 0.0 or u >= 1.0:
        return 0.0
    if u <= 0.5:
        return u * 2.0
    return (1.0 - u) * 2.0


def build_memory_flashback(
    image_paths: list[Path],
    output_path: str | Path,
    aspect: str = "16:9",
    fps: int = 30,
    clip_duration: float = 0.30,
    zoom_start: float = 1.32,
    fit_mode: str = "cover",
    motion_blur: bool = True,
    bgm_path: str | Path | None = None,
    bgm_volume_db: float = -6.0,
    crf: int = 18,
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    width, height = parse_aspect_resolution(aspect)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    stride = clip_duration * 0.5
    n_imgs = len(image_paths)
    total_dur = (n_imgs - 1) * stride + clip_duration
    total_frames = max(1, int(round(total_dur * fps)))

    # Pre-fit images into memory (sized cleanly at output resolution for fast transform)
    # Using oversized canvas only up to 1.35x if needed; at output resolution Bilinear is crisp & fast
    base_scale = min(1.35, max(1.0, zoom_start))
    prep_w = int(round(width * base_scale))
    prep_h = int(round(height * base_scale))

    prepared: list[Image.Image] = []
    for p in image_paths:
        with Image.open(p) as raw:
            prepared.append(fit_image_to_canvas(raw, prep_w, prep_h, mode=fit_mode))

    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
    ]

    if bgm_path:
        fade_out_st = max(0.0, total_dur - min(1.0, total_dur * 0.25))
        cmd += [
            "-stream_loop",
            "-1",
            "-i",
            str(bgm_path),
            "-filter_complex",
            (
                f"[1:a]atrim=0:{total_dur:.3f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo,"
                f"volume={bgm_volume_db}dB,"
                f"afade=t=in:st=0:d=0.35,"
                f"afade=t=out:st={fade_out_st:.3f}:d={min(1.0, total_dur * 0.25):.3f},"
                f"loudnorm=I=-14:TP=-1.0:LRA=11[aout]"
            ),
            "-map",
            "0:v",
            "-map",
            "[aout]",
        ]
    else:
        cmd += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map",
            "0:v",
            "-map",
            "1:a",
        ]

    cmd += [
        "-t",
        f"{total_dur:.4f}",
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
        "-shortest",
        "-movflags",
        "+faststart",
        str(out),
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for f_idx in range(total_frames):
            t = f_idx / float(fps)
            # Determine active images (at most 2 at any instant because stride = clip_duration / 2)
            canvas = np.zeros((height, width, 3), dtype=np.float32)

            k_min = max(0, int((t - clip_duration) / stride) - 1)
            k_max = min(n_imgs - 1, int(t / stride) + 1)

            for k in range(k_min, k_max + 1):
                t_start = k * stride
                t_local = t - t_start
                if t_local < 0.0 or t_local >= clip_duration:
                    continue
                u = t_local / clip_duration
                alpha = _opacity_triangle(u)
                if alpha <= 1e-4:
                    continue
                layer = _render_zoom_out_layer(
                    prepared[k],
                    width,
                    height,
                    u=u,
                    zoom_start=zoom_start,
                    motion_blur=motion_blur,
                )
                # Dual-track additive linear cross-dissolve (alphas sum to 1.0 in overlap)
                canvas += layer * alpha

            frame_u8 = np.clip(canvas, 0.0, 255.0).astype(np.uint8)
            proc.stdin.write(frame_u8.tobytes())

        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg 渲染回忆快闪失败 (exit={ret}): {stderr}")
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="生成「回忆快闪」公式化视频片段")
    parser.add_argument("--images", nargs="+", default=None, help="按顺序传入的图片文件路径列表")
    parser.add_argument("--images-dir", default=None, help="包含回忆图片的文件夹路径（自然排序读取）")
    parser.add_argument("--output", required=True, help="输出视频路径 (.mp4)")
    parser.add_argument("--aspect", default="16:9", help="画幅规格: 16:9 / 9:16 / 1:1 / WxH")
    parser.add_argument("--fps", type=int, default=30, help="输出帧率（推荐 30 或 60，默认 30）")
    parser.add_argument(
        "--clip-duration",
        type=float,
        default=0.30,
        help="单张图片总时长（秒，默认 0.30；双轨交错步长自动为其一半 0.15s）",
    )
    parser.add_argument(
        "--zoom-start",
        type=float,
        default=1.32,
        help="「动感缩小」起始放大倍率（默认 1.32）",
    )
    parser.add_argument(
        "--fit-mode",
        choices=["cover", "blur_fit"],
        default="cover",
        help="图片画幅适配模式（默认 cover 居中裁切满屏）",
    )
    parser.add_argument("--no-motion-blur", action="store_true", help="关闭开场轻微动感缩放模糊")
    parser.add_argument("--bgm", default=None, help="可选：配套 BGM 音频路径")
    parser.add_argument("--bgm-volume-db", type=float, default=-6.0, help="BGM 音量增益 dB")
    args = parser.parse_args()

    imgs = collect_images(args.images, args.images_dir)
    out = build_memory_flashback(
        image_paths=imgs,
        output_path=args.output,
        aspect=args.aspect,
        fps=args.fps,
        clip_duration=args.clip_duration,
        zoom_start=args.zoom_start,
        fit_mode=args.fit_mode,
        motion_blur=not args.no_motion_blur,
        bgm_path=args.bgm,
        bgm_volume_db=args.bgm_volume_db,
    )
    stride = args.clip_duration * 0.5
    total_dur = (len(imgs) - 1) * stride + args.clip_duration
    print(f"回忆快闪已生成: {out} ({len(imgs)} 张图, {total_dur:.2f}s @ {args.fps}fps, {args.aspect})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
