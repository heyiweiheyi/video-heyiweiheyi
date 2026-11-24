#!/usr/bin/env python3
"""Build a '六分屏闪白卡点' (6-Strip Split-Screen Beat-Synced Flash Wipe) video clip.

Splits canvas into N vertical strips (default 6) with crisp hairline dividers,
reveals image 1 strip-by-strip on music beats, then replaces strips image-by-image
on subsequent beats, applying a 3-frame Brightness+Contrast max flash burst at
the start and end of every strip transition.
"""

from __future__ import annotations

import argparse
import random
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

FOUNDATIONS_SCRIPTS = Path(__file__).resolve().parents[3] / "foundations" / "scripts"
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
        raise ValueError(f"六分屏闪白卡点至少需要 2 张图片（推荐 4–8 张），当前仅检测到 {len(paths)} 张。")
    return paths


def compute_strip_order(num_strips: int, order: str, seed: int = 42) -> list[int]:
    if order == "left-to-right":
        return list(range(num_strips))
    if order == "right-to-left":
        return list(range(num_strips - 1, -1, -1))
    if order == "alternate":
        res: list[int] = []
        l, r = 0, num_strips - 1
        while l <= r:
            res.append(l)
            if l != r:
                res.append(r)
            l += 1
            r -= 1
        return res
    if order == "random":
        rng = random.Random(seed)
        cols = list(range(num_strips))
        rng.shuffle(cols)
        return cols
    # Default: center-out (e.g., for 6 strips: [2, 3, 1, 4, 0, 5])
    mid_left = (num_strips - 1) // 2
    res = []
    left, right = mid_left, mid_left + 1
    while left >= 0 or right < num_strips:
        if left >= 0:
            res.append(left)
            left -= 1
        if right < num_strips:
            res.append(right)
            right += 1
    return res


def detect_audio_beats(
    bgm_path: str | Path,
    needed_beats: int,
    min_gap_sec: float = 0.18,
    fallback_interval: float = 0.25,
) -> list[float]:
    """Lightweight pure-numpy audio onset/peak detector via FFmpeg PCM decode."""
    ffmpeg = get_ffmpeg_exe()
    sr = 22050
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(bgm_path),
            "-ac",
            "1",
            "-ar",
            str(sr),
            "-f",
            "f32le",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if proc.returncode != 0 or len(proc.stdout) < sr:
        return [0.15 + i * fallback_interval for i in range(needed_beats)]

    samples = np.frombuffer(proc.stdout, dtype=np.float32)
    hop = 512
    win = 1024
    n_hops = max(1, (len(samples) - win) // hop)
    if n_hops < 8:
        return [0.15 + i * fallback_interval for i in range(needed_beats)]

    # Compute short-time RMS energy and positive onset flux
    frames = np.lib.stride_tricks.as_strided(
        samples,
        shape=(n_hops, win),
        strides=(samples.strides[0] * hop, samples.strides[0]),
    )
    rms = np.sqrt(np.mean(frames * frames, axis=1) + 1e-12)
    flux = np.maximum(0.0, np.diff(rms, prepend=rms[0]))

    # Local adaptive threshold
    kernel = 15
    local_mean = np.convolve(flux, np.ones(kernel) / kernel, mode="same")
    thresh = local_mean * 1.45 + np.std(flux) * 0.25

    min_hop_gap = max(1, int(round(min_gap_sec * sr / hop)))
    peaks: list[float] = []
    last_idx = -min_hop_gap
    for idx in range(1, len(flux) - 1):
        if idx - last_idx < min_hop_gap:
            continue
        if flux[idx] > thresh[idx] and flux[idx] >= flux[idx - 1] and flux[idx] >= flux[idx + 1]:
            t = idx * hop / float(sr)
            if t >= 0.05:
                peaks.append(round(t, 4))
                last_idx = idx
        if len(peaks) >= needed_beats:
            break

    # If BGM has fewer detected peaks than needed, extrapolate cleanly using median gap
    if len(peaks) < needed_beats:
        if len(peaks) >= 3:
            diffs = np.diff(peaks)
            med_gap = float(np.clip(np.median(diffs), 0.18, 0.65))
        else:
            med_gap = fallback_interval
        start_t = peaks[-1] + med_gap if peaks else 0.15
        while len(peaks) < needed_beats:
            peaks.append(round(start_t, 4))
            start_t += med_gap

    return peaks[:needed_beats]


def apply_brightness_contrast_flash(strip_arr: np.ndarray, intensity: float) -> np.ndarray:
    """Replicate Jianying Brightness+Contrast max flash burst cleanly."""
    if intensity <= 1e-4:
        return strip_arr
    # Quadratic decay makes the 3-frame flash punchy and crisp
    s = float(intensity) ** 1.6
    out = (strip_arr - 128.0) * (1.0 + 1.35 * s) + 128.0 + 165.0 * s
    return np.clip(out, 0.0, 255.0)


def build_split_screen_beat_flash(
    image_paths: list[Path],
    output_path: str | Path,
    aspect: str = "16:9",
    fps: int = 30,
    num_strips: int = 6,
    order: str = "center-out",
    beat_interval: float = 0.25,
    bpm: float | None = None,
    explicit_beats: list[float] | None = None,
    auto_beats: bool = False,
    hold_beats: int = 1,
    end_hold_sec: float = 0.85,
    flash_frames: int = 3,
    gap_px: int = 3,
    fit_mode: str = "cover",
    bgm_path: str | Path | None = None,
    bgm_volume_db: float = -6.0,
    crf: int = 18,
) -> Path:
    ffmpeg = get_ffmpeg_exe()
    width, height = parse_aspect_resolution(aspect)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    n_imgs = len(image_paths)
    num_strips = max(2, min(12, num_strips))
    strip_order = compute_strip_order(num_strips, order)

    # Determine beat timestamps for all strip switch events
    step_sec = (60.0 / bpm) * 0.5 if bpm and bpm > 0 else beat_interval
    total_beat_slots = n_imgs * num_strips + max(0, n_imgs - 1) * max(0, hold_beats)

    if explicit_beats and len(explicit_beats) >= total_beat_slots:
        beats = sorted(explicit_beats)[:total_beat_slots]
    elif auto_beats and bgm_path:
        beats = detect_audio_beats(bgm_path, needed_beats=total_beat_slots, fallback_interval=step_sec)
    else:
        beats = [round(0.12 + i * step_sec, 4) for i in range(total_beat_slots)]

    # Build per-column timeline: list of (img_idx, start_frame, end_frame_or_None)
    col_events: list[list[tuple[int, int]]] = [[] for _ in range(num_strips)]
    beat_cursor = 0
    for img_idx in range(n_imgs):
        for col in strip_order:
            t_beat = beats[beat_cursor]
            beat_cursor += 1
            col_events[col].append((img_idx, int(round(t_beat * fps))))
        if img_idx < n_imgs - 1:
            beat_cursor += max(0, hold_beats)

    last_event_time = beats[-1]
    total_dur = last_event_time + max(0.4, end_hold_sec)
    total_frames = max(1, int(round(total_dur * fps)))

    # Pre-fit all images to exact (width, height) float32 arrays
    img_arrays: list[np.ndarray] = []
    for p in image_paths:
        with Image.open(p) as raw:
            fitted = fit_image_to_canvas(raw, width, height, mode=fit_mode)
            img_arrays.append(np.asarray(fitted, dtype=np.float32))

    # Precompute vertical strip boundaries with crisp hairline dividers
    half_gap_l = gap_px // 2
    half_gap_r = gap_px - half_gap_l
    strip_bounds: list[tuple[int, int]] = []
    for c in range(num_strips):
        x1 = int(round(c * width / num_strips)) + (half_gap_l if c > 0 else 0)
        x2 = int(round((c + 1) * width / num_strips)) - (half_gap_r if c < num_strips - 1 else 0)
        strip_bounds.append((x1, x2))

    # Scale flash_frames proportionally if fps != 30 (3 frames @30fps = 0.10s)
    eff_flash_frames = max(2, int(round(flash_frames * (fps / 30.0))))

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
        fade_out_dur = min(1.0, total_dur * 0.2)
        fade_out_st = max(0.0, total_dur - fade_out_dur)
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
                f"afade=t=in:st=0:d=0.15,"
                f"afade=t=out:st={fade_out_st:.3f}:d={fade_out_dur:.3f},"
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
            canvas = np.zeros((height, width, 3), dtype=np.uint8)

            for c in range(num_strips):
                events = col_events[c]
                active_slot = -1
                for slot_i, (_img_i, start_f) in enumerate(events):
                    if f_idx >= start_f:
                        active_slot = slot_i
                    else:
                        break
                if active_slot < 0:
                    continue

                img_i, start_f = events[active_slot]
                next_start_f = events[active_slot + 1][1] if active_slot + 1 < len(events) else None

                # Compute 3-frame opening flash & 3-frame pre-switch closing flash
                flash_in = 0.0
                dt_in = f_idx - start_f
                if 0 <= dt_in < eff_flash_frames:
                    flash_in = 1.0 - (dt_in / float(eff_flash_frames))

                flash_out = 0.0
                if next_start_f is not None:
                    dt_out = (next_start_f - 1) - f_idx
                    if 0 <= dt_out < eff_flash_frames:
                        flash_out = 1.0 - (dt_out / float(eff_flash_frames))

                intensity = max(flash_in, flash_out)
                x1, x2 = strip_bounds[c]
                strip = img_arrays[img_i][:, x1:x2, :]
                if intensity > 1e-4:
                    strip = apply_brightness_contrast_flash(strip, intensity)
                canvas[:, x1:x2, :] = strip.astype(np.uint8)

            proc.stdin.write(canvas.tobytes())

        proc.stdin.close()
        stderr = proc.stderr.read().decode("utf-8", errors="replace") if proc.stderr else ""
        ret = proc.wait()
        if ret != 0:
            raise RuntimeError(f"FFmpeg 渲染六分屏闪白卡点失败 (exit={ret}): {stderr}")
    finally:
        if proc.stdin and not proc.stdin.closed:
            proc.stdin.close()

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="生成「六分屏闪白卡点」公式化视频片段")
    parser.add_argument("--images", nargs="+", default=None, help="按顺序传入的图片文件路径列表")
    parser.add_argument("--images-dir", default=None, help="包含图片的文件夹路径（自然排序读取）")
    parser.add_argument("--output", required=True, help="输出视频路径 (.mp4)")
    parser.add_argument("--aspect", default="16:9", help="画幅规格: 16:9 / 9:16 / 1:1 / WxH")
    parser.add_argument("--fps", type=int, default=30, help="输出帧率（默认 30）")
    parser.add_argument("--strips", type=int, default=6, help="竖向分屏等分数（默认 6）")
    parser.add_argument(
        "--order",
        choices=["center-out", "left-to-right", "right-to-left", "alternate", "random"],
        default="center-out",
        help="分屏逐格点亮与替换顺序（默认 center-out 中间向外）",
    )
    parser.add_argument("--beat-interval", type=float, default=0.25, help="固定节拍间隔秒数（默认 0.25s）")
    parser.add_argument("--bpm", type=float, default=None, help="可选：按歌曲 BPM 自动换算半拍间隔")
    parser.add_argument("--beats", default=None, help="可选：逗号分隔的精确节拍时间戳（秒）")
    parser.add_argument("--auto-beats", action="store_true", help="对传入的 --bgm 自动检测波峰卡点")
    parser.add_argument("--hold-beats", type=int, default=1, help="每张图拼满后的停留拍数（默认 1）")
    parser.add_argument("--end-hold-sec", type=float, default=0.85, help="最后一张图拼满后定格时长（秒）")
    parser.add_argument("--flash-frames", type=int, default=3, help="片头/片尾闪白持续帧数（30fps 基准默认 3 帧）")
    parser.add_argument("--gap", type=int, default=3, help="分屏栏间暗缝像素宽度（默认 3px）")
    parser.add_argument("--fit-mode", choices=["cover", "blur_fit"], default="cover", help="图片画幅适配模式")
    parser.add_argument("--bgm", default=None, help="可选：卡点背景音乐路径")
    parser.add_argument("--bgm-volume-db", type=float, default=-6.0, help="BGM 基础音量 dB")
    args = parser.parse_args()

    explicit = None
    if args.beats:
        explicit = [float(x.strip()) for x in args.beats.split(",") if x.strip()]

    imgs = collect_images(args.images, args.images_dir)
    out = build_split_screen_beat_flash(
        image_paths=imgs,
        output_path=args.output,
        aspect=args.aspect,
        fps=args.fps,
        num_strips=args.strips,
        order=args.order,
        beat_interval=args.beat_interval,
        bpm=args.bpm,
        explicit_beats=explicit,
        auto_beats=args.auto_beats,
        hold_beats=args.hold_beats,
        end_hold_sec=args.end_hold_sec,
        flash_frames=args.flash_frames,
        gap_px=args.gap,
        fit_mode=args.fit_mode,
        bgm_path=args.bgm,
        bgm_volume_db=args.bgm_volume_db,
    )
    print(f"六分屏闪白卡点已生成: {out} ({len(imgs)} 张图, {args.strips} 分屏, order={args.order})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
