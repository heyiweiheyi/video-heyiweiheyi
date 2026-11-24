#!/usr/bin/env python3
"""Shared cross-platform FFmpeg/media utilities for video-heyiweiheyi."""

from __future__ import annotations

import os
import re
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageFilter, ImageOps


ASPECT_MAP: dict[str, tuple[int, int]] = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "4:3": (1440, 1080),
    "4k-16:9": (3840, 2160),
    "4k-9:16": (2160, 3840),
}


def get_ffmpeg_exe() -> str:
    """Locate ffmpeg from system PATH first, then fall back to imageio-ffmpeg."""
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg  # type: ignore

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "未检测到 ffmpeg。请安装 ffmpeg 并加入系统 PATH，或运行 `pip install imageio-ffmpeg`。"
        ) from exc


def get_ffprobe_exe() -> str | None:
    """Locate ffprobe if available on PATH (optional)."""
    return shutil.which("ffprobe")


def parse_aspect_resolution(aspect: str) -> tuple[int, int]:
    """Parse aspect label like '16:9', '9:16', or explicit '1920x1080'."""
    key = aspect.strip().lower()
    if key in ASPECT_MAP:
        return ASPECT_MAP[key]
    m = re.fullmatch(r"(\d+)\s*[x×]\s*(\d+)", key)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        return (w - (w % 2), h - (h % 2))
    raise ValueError(f"不支持的画幅规格: {aspect}（可用 16:9、9:16、1:1 或 WxH）")


def check_mp4_faststart(path: str | Path) -> bool | None:
    """Check whether MP4 'moov' atom precedes 'mdat' atom (faststart)."""
    p = Path(path)
    if not p.is_file() or p.suffix.lower() not in {".mp4", ".mov", ".m4v"}:
        return None
    moov_pos = None
    mdat_pos = None
    size_total = p.stat().st_size
    pos = 0
    with p.open("rb") as fh:
        while pos + 8 <= size_total:
            fh.seek(pos)
            header = fh.read(8)
            if len(header) < 8:
                break
            atom_size, atom_type = struct.unpack(">I4s", header)
            if atom_size == 1:
                ext = fh.read(8)
                if len(ext) < 8:
                    break
                atom_size = struct.unpack(">Q", ext)[0]
            elif atom_size == 0:
                atom_size = size_total - pos
            if atom_size < 8:
                break
            if atom_type == b"moov" and moov_pos is None:
                moov_pos = pos
            elif atom_type == b"mdat" and mdat_pos is None:
                mdat_pos = pos
            if moov_pos is not None and mdat_pos is not None:
                break
            pos += atom_size
    if moov_pos is None or mdat_pos is None:
        return None
    return moov_pos < mdat_pos


def _parse_hms_to_seconds(hms: str) -> float:
    parts = hms.strip().split(":")
    if len(parts) != 3:
        return 0.0
    return int(parts[0]) * 3600.0 + int(parts[1]) * 60.0 + float(parts[2])


def probe_media_info(path: str | Path) -> dict[str, Any]:
    """Probe basic video/audio metadata using ffmpeg (no ffprobe dependency required)."""
    ffmpeg = get_ffmpeg_exe()
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stderr = proc.stderr

    info: dict[str, Any] = {
        "path": str(path),
        "duration_sec": None,
        "width": None,
        "height": None,
        "fps": None,
        "video_codec": None,
        "pix_fmt": None,
        "has_audio": False,
        "audio_codec": None,
        "sample_rate": None,
        "channels": None,
        "faststart": check_mp4_faststart(path),
    }

    m_dur = re.search(r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)", stderr)
    if m_dur:
        info["duration_sec"] = round(_parse_hms_to_seconds(m_dur.group(1)), 3)

    m_v = re.search(r"Stream #\d+:\d+.*?: Video:\s*([^\n]+)", stderr)
    if m_v:
        vline = m_v.group(1)
        info["video_codec"] = vline.split(",")[0].strip().split()[0].lower()
        m_pix = re.search(r",\s*(yuv\w+|rgb\w+|bgr\w+|gray\w*|nv12|gbrp\w*)", vline)
        if m_pix:
            info["pix_fmt"] = m_pix.group(1).split("(")[0]
        m_res = re.search(r",\s*(\d{2,5})x(\d{2,5})\b", vline)
        if m_res:
            info["width"] = int(m_res.group(1))
            info["height"] = int(m_res.group(2))
        m_fps = re.search(r"(\d+(?:\.\d+)?)\s*fps", vline)
        if m_fps:
            info["fps"] = float(m_fps.group(1))

    m_a = re.search(r"Stream #\d+:\d+.*?: Audio:\s*([^\n]+)", stderr)
    if m_a:
        aline = m_a.group(1)
        info["has_audio"] = True
        info["audio_codec"] = aline.split(",")[0].strip().split()[0].lower()
        m_sr = re.search(r"(\d+)\s*Hz", aline)
        if m_sr:
            info["sample_rate"] = int(m_sr.group(1))
        if "stereo" in aline:
            info["channels"] = 2
        elif "mono" in aline:
            info["channels"] = 1
        else:
            m_ch = re.search(r"(\d+)\s*channels", aline)
            if m_ch:
                info["channels"] = int(m_ch.group(1))

    return info


def fit_image_to_canvas(
    img: Image.Image,
    target_w: int,
    target_h: int,
    mode: str = "cover",
) -> Image.Image:
    """Fit any image onto (target_w, target_h) without distortion.

    mode='cover': center crop to fill canvas cleanly.
    mode='blur_fit': blurred darkened background + centered intact foreground.
    """
    img = ImageOps.exif_transpose(img).convert("RGB")
    if mode == "blur_fit":
        bg = ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)
        bg = bg.filter(ImageFilter.GaussianBlur(radius=max(20, min(target_w, target_h) // 35)))
        bg_arr = (np.asarray(bg, dtype=np.float32) * 0.45).clip(0, 255).astype(np.uint8)
        canvas = Image.fromarray(bg_arr, mode="RGB")
        fg = img.copy()
        fg.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
        x = (target_w - fg.width) // 2
        y = (target_h - fg.height) // 2
        canvas.paste(fg, (x, y))
        return canvas
    return ImageOps.fit(img, (target_w, target_h), method=Image.Resampling.LANCZOS)


def ease_in_out_cubic(t: float) -> float:
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        return 4.0 * t * t * t
    return 1.0 - pow(-2.0 * t + 2.0, 3) / 2.0


def image_to_ken_burns(
    image_path: str | Path,
    output_path: str | Path,
    duration: float = 4.0,
    aspect: str = "16:9",
    fps: int = 30,
    zoom_start: float = 1.0,
    zoom_end: float = 1.08,
    pan_x: float = 0.0,
    pan_y: float = 0.0,
    fit_mode: str = "cover",
    crf: int = 18,
) -> Path:
    """Convert a static image into a smooth Ken Burns motion clip with silent 48kHz stereo audio."""
    ffmpeg = get_ffmpeg_exe()
    width, height = parse_aspect_resolution(aspect)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with Image.open(image_path) as raw:
        max_zoom = max(zoom_start, zoom_end, 1.0)
        # Render slightly oversized base for crisp sub-pixel zoom/pan
        pad_scale = max_zoom * 1.06 + max(abs(pan_x), abs(pan_y))
        base_w = int(round(width * pad_scale))
        base_h = int(round(height * pad_scale))
        base_img = fit_image_to_canvas(raw, base_w, base_h, mode=fit_mode)

    total_frames = max(1, int(round(duration * fps)))
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
        "-f",
        "lavfi",
        "-i",
        "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-t",
        f"{duration:.4f}",
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
        for i in range(total_frames):
            progress = i / max(1, total_frames - 1)
            eased = ease_in_out_cubic(progress)
            z = zoom_start + (zoom_end - zoom_start) * eased
            crop_w = base_w / z
            crop_h = base_h / z
            cx = base_w * (0.5 + pan_x * (eased - 0.5))
            cy = base_h * (0.5 + pan_y * (eased - 0.5))
            x1 = max(0.0, min(base_w - crop_w, cx - crop_w / 2.0))
            y1 = max(0.0, min(base_h - crop_h, cy - crop_h / 2.0))
            frame = base_img.transform(
                (width, height),
                Image.Transform.EXTENT,
                (x1, y1, x1 + crop_w, y1 + crop_h),
                resample=Image.Resampling.BICUBIC,
            )
            proc.stdin.write(frame.tobytes())
        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg Ken Burns 渲染失败 (exit={ret}): {stderr}")
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()
    return out


def normalize_clip(
    input_path: str | Path,
    output_path: str | Path,
    aspect: str = "16:9",
    fps: int = 30,
    fit_mode: str = "cover",
    crf: int = 18,
) -> Path:
    """Standardize any video clip to uniform resolution, CFR fps, yuv420p, and 48kHz stereo audio."""
    ffmpeg = get_ffmpeg_exe()
    width, height = parse_aspect_resolution(aspect)
    info = probe_media_info(input_path)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if fit_mode == "blur_fit":
        vf = (
            f"split=2[bg][fg];"
            f"[bg]scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},boxblur=25:2,eq=brightness=-0.12[bgb];"
            f"[fg]scale={width}:{height}:force_original_aspect_ratio=decrease[fgb];"
            f"[bgb][fgb]overlay=(W-w)/2:(H-h)/2,fps={fps},setsar=1,format=yuv420p"
        )
    else:
        vf = (
            f"scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},fps={fps},setsar=1,format=yuv420p"
        )

    cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(input_path)]
    if info["has_audio"]:
        cmd += [
            "-vf",
            vf,
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
    else:
        cmd += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-filter_complex",
            f"[0:v]{vf}[vout]",
            "-map",
            "[vout]",
            "-map",
            "1:a",
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

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"标准化转码失败: {res.stderr}")
    return out
