#!/usr/bin/env python3
"""Extract keyframe Contact Sheet with timestamp labels and 16:9 / 9:16 platform safe-zone guides."""

from __future__ import annotations

import argparse
import math
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ffmpeg_utils import get_ffmpeg_exe, probe_media_info


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "C:/Windows/Fonts/consolab.ttf",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/arialbd.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]
    for p in candidates:
        if Path(p).is_file():
            try:
                return ImageFont.truetype(p, size=size)
            except Exception:
                pass
    return ImageFont.load_default()


def _draw_dashed_rect(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    color: tuple[int, int, int],
    width: int = 2,
    dash: int = 8,
    gap: int = 6,
) -> None:
    x1, y1, x2, y2 = box
    # Top and bottom
    x = x1
    while x < x2:
        draw.line([(x, y1), (min(x + dash, x2), y1)], fill=color, width=width)
        draw.line([(x, y2), (min(x + dash, x2), y2)], fill=color, width=width)
        x += dash + gap
    # Left and right
    y = y1
    while y < y2:
        draw.line([(x1, y), (x1, min(y + dash, y2))], fill=color, width=width)
        draw.line([(x2, y), (x2, min(y + dash, y2))], fill=color, width=width)
        y += dash + gap


def _draw_safe_zone(img: Image.Image, safe_zone: str) -> Image.Image:
    if safe_zone == "none":
        return img
    w, h = img.size
    out = img.copy()
    draw = ImageDraw.Draw(out)

    mode = safe_zone
    if mode == "auto":
        mode = "9:16" if h > w else "16:9"

    if mode == "9:16":
        # Douyin / Shorts / Reels safe zone: top 13%, bottom 23%, right 15%, left 5.5%
        box = (
            int(w * 0.055),
            int(h * 0.13),
            int(w * 0.85),
            int(h * 0.77),
        )
        _draw_dashed_rect(draw, box, color=(0, 230, 180), width=2)
    else:
        # 16:9 title/subtitle safe zone: 5% left/right/top, 10% bottom
        box = (
            int(w * 0.05),
            int(h * 0.05),
            int(w * 0.95),
            int(h * 0.90),
        )
        _draw_dashed_rect(draw, box, color=(0, 230, 180), width=2)
    return out


def extract_contact_sheet(
    input_path: Path,
    output_path: Path,
    count: int = 12,
    timestamps: list[float] | None = None,
    cols: int | None = None,
    thumb_width: int = 420,
    safe_zone: str = "auto",
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    info = probe_media_info(input_path)
    duration = info["duration_sec"] or 1.0
    vid_w = info["width"] or 1920
    vid_h = info["height"] or 1080

    if timestamps:
        sample_times = [max(0.0, min(duration - 0.02, t)) for t in timestamps]
    else:
        n = max(2, count)
        if n == 2:
            sample_times = [0.05, max(0.05, duration - 0.05)]
        else:
            start_t = min(0.05, duration * 0.02)
            end_t = max(start_t, duration - min(0.08, duration * 0.03))
            step = (end_t - start_t) / (n - 1)
            sample_times = [start_t + i * step for i in range(n)]

    if cols is None:
        cols = 4 if vid_w >= vid_h else 6
    rows = math.ceil(len(sample_times) / cols)

    thumb_h = max(120, int(round(thumb_width * vid_h / vid_w)))
    pad = 14
    header_h = 54
    sheet_w = cols * thumb_width + (cols + 1) * pad
    sheet_h = header_h + rows * thumb_h + (rows + 1) * pad

    sheet = Image.new("RGB", (sheet_w, sheet_h), (18, 20, 26))
    sheet_draw = ImageDraw.Draw(sheet)
    title_font = _load_font(20)
    badge_font = _load_font(16)

    header_text = (
        f"Contact Sheet | {input_path.name} | {vid_w}x{vid_h} @ {info['fps']}fps | "
        f"{duration:.2f}s | SafeZone: {safe_zone}"
    )
    sheet_draw.text((pad, 15), header_text, fill=(235, 240, 248), font=title_font)

    with tempfile.TemporaryDirectory() as tmpdir:
        for idx, ts in enumerate(sample_times):
            frame_file = Path(tmpdir) / f"frame_{idx:03d}.png"
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-ss",
                    f"{ts:.3f}",
                    "-i",
                    str(input_path),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "2",
                    str(frame_file),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            with Image.open(frame_file) as fimg:
                thumb = fimg.convert("RGB").resize((thumb_width, thumb_h), Image.Resampling.LANCZOS)
            thumb = _draw_safe_zone(thumb, safe_zone=safe_zone)

            tdraw = ImageDraw.Draw(thumb)
            label = f"#{idx + 1:02d}  {ts:06.2f}s"
            bbox = tdraw.textbbox((0, 0), label, font=badge_font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            tdraw.rectangle([8, 8, 8 + tw + 14, 8 + th + 10], fill=(10, 12, 18))
            tdraw.text((15, 12), label, fill=(255, 235, 130), font=badge_font)

            r = idx // cols
            c = idx % cols
            x = pad + c * (thumb_width + pad)
            y = header_h + pad + r * (thumb_h + pad)
            sheet.paste(thumb, (x, y))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="video-heyiweiheyi 关键帧联系表抽帧目检工具")
    parser.add_argument("--input", required=True, help="待检视频路径 (.mp4)")
    parser.add_argument("--output", required=True, help="输出联系表图片路径 (.png)")
    parser.add_argument("--count", type=int, default=12, help="均匀抽帧数量（默认 12）")
    parser.add_argument(
        "--timestamps",
        default=None,
        help="可选：逗号分隔的精确抽帧时间点（秒），如 0.1,1.5,3.0,4.8",
    )
    parser.add_argument("--cols", type=int, default=None, help="每行列数")
    parser.add_argument("--thumb-width", type=int, default=420, help="单帧缩略图宽度（默认 420px）")
    parser.add_argument(
        "--safe-zone",
        choices=["auto", "16:9", "9:16", "none"],
        default="auto",
        help="安全区参考虚线框模式（默认 auto）",
    )
    args = parser.parse_args()

    ts_list = None
    if args.timestamps:
        ts_list = [float(x.strip()) for x in args.timestamps.split(",") if x.strip()]

    out = extract_contact_sheet(
        input_path=Path(args.input),
        output_path=Path(args.output),
        count=args.count,
        timestamps=ts_list,
        cols=args.cols,
        thumb_width=args.thumb_width,
        safe_zone=args.safe_zone,
    )
    print(f"联系表已生成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
