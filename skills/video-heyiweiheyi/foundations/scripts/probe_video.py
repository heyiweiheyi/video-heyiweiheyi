#!/usr/bin/env python3
"""Automated technical audit probe for delivered videos (video-heyiweiheyi)."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ffmpeg_utils import get_ffmpeg_exe, parse_aspect_resolution, probe_media_info


def analyze_audio_loudness(path: Path) -> dict[str, Any]:
    """Measure EBU R128 integrated LUFS & True Peak plus max volume."""
    ffmpeg = get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-af",
            "ebur128=peak=true",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    stderr = proc.stderr
    result: dict[str, Any] = {
        "integrated_lufs": None,
        "true_peak_dbtp": None,
        "lra_lu": None,
    }
    m_i = re.search(r"Integrated loudness:\s*\n\s*I:\s*(-?\d+(?:\.\d+)?)\s*LUFS", stderr)
    if m_i:
        result["integrated_lufs"] = float(m_i.group(1))
    m_lra = re.search(r"LRA:\s*(-?\d+(?:\.\d+)?)\s*LU", stderr)
    if m_lra:
        result["lra_lu"] = float(m_lra.group(1))
    m_tp = re.search(r"True peak:\s*\n\s*Peak:\s*(-?\d+(?:\.\d+)?)\s*dBFS", stderr)
    if m_tp:
        result["true_peak_dbtp"] = float(m_tp.group(1))
    return result


def detect_black_frames(path: Path, min_dur: float = 0.25) -> list[dict[str, float]]:
    """Detect sustained black segments (useful for catching accidental black-frame gaps)."""
    ffmpeg = get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-i",
            str(path),
            "-vf",
            f"blackdetect=d={min_dur}:pix_th=0.05",
            "-an",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    segments: list[dict[str, float]] = []
    for m in re.finditer(
        r"black_start:(\d+(?:\.\d+)?)\s+black_end:(\d+(?:\.\d+)?)\s+black_duration:(\d+(?:\.\d+)?)",
        proc.stderr,
    ):
        segments.append(
            {
                "start": round(float(m.group(1)), 3),
                "end": round(float(m.group(2)), 3),
                "duration": round(float(m.group(3)), 3),
            }
        )
    return segments


def audit_video(
    input_path: Path,
    expected_aspect: str | None = None,
    expected_fps: float | None = None,
    check_loudness: bool = True,
) -> dict[str, Any]:
    info = probe_media_info(input_path)
    issues: list[str] = []
    warnings: list[str] = []

    if info["video_codec"] != "h264":
        issues.append(f"视频编码为 {info['video_codec']}，建议统一使用 h264 (libx264) 以保证全平台兼容。")
    if info["pix_fmt"] != "yuv420p":
        issues.append(f"像素格式为 {info['pix_fmt']}，必须使用 yuv420p 避免手机/微信黑屏无法播放。")
    if info["faststart"] is False:
        issues.append("未启用 MP4 faststart（moov 原子位于 mdat 之后），请加 `-movflags +faststart`。")

    if expected_aspect:
        exp_w, exp_h = parse_aspect_resolution(expected_aspect)
        if info["width"] != exp_w or info["height"] != exp_h:
            issues.append(
                f"分辨率为 {info['width']}x{info['height']}，与期望画幅 {expected_aspect} ({exp_w}x{exp_h}) 不符。"
            )

    if expected_fps and info["fps"] is not None:
        if abs(info["fps"] - expected_fps) > 0.2:
            warnings.append(f"帧率为 {info['fps']} fps，与期望 {expected_fps} fps 存在偏差。")

    loudness: dict[str, Any] = {}
    if info["has_audio"]:
        if info["sample_rate"] != 48000:
            warnings.append(f"音频采样率为 {info['sample_rate']} Hz，建议统一为 48000 Hz。")
        if check_loudness:
            loudness = analyze_audio_loudness(input_path)
            lufs = loudness.get("integrated_lufs")
            tp = loudness.get("true_peak_dbtp")
            if lufs is not None and lufs > -10.5:
                warnings.append(f"综合响度偏高 ({lufs} LUFS)，目标建议 -14 ~ -16 LUFS。")
            elif lufs is not None and -60.0 < lufs < -22.0:
                warnings.append(f"综合响度偏低 ({lufs} LUFS)，目标建议 -14 ~ -16 LUFS。")
            if tp is not None and tp > -0.5:
                issues.append(f"音频真峰值过高 ({tp} dBTP > -0.5 dBTP)，存在削波爆音风险。")
    else:
        warnings.append("成片无音频轨（如为刻意纯无声片段可忽略；否则请补充 BGM 或静音标准轨）。")

    black_segments = detect_black_frames(input_path)
    if black_segments:
        warnings.append(f"检测到 {len(black_segments)} 处持续 >=0.25s 的黑帧区间（若非刻意淡入/淡出请目检确认）。")

    return {
        "status": "PASS" if not issues else "FAIL",
        "media": info,
        "loudness": loudness,
        "black_segments": black_segments,
        "issues": issues,
        "warnings": warnings,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="video-heyiweiheyi 硬指标自动化体检工具")
    parser.add_argument("--input", required=True, help="待检视频路径 (.mp4)")
    parser.add_argument("--expected-aspect", default=None, help="期望画幅，如 16:9 / 9:16 / 1920x1080")
    parser.add_argument("--expected-fps", type=float, default=None, help="期望帧率，如 30 或 60")
    parser.add_argument("--no-loudness", action="store_true", help="跳过 EBU R128 响度分析以提速")
    parser.add_argument("--json", action="store_true", help="以纯 JSON 格式输出结果")
    args = parser.parse_args()

    target = Path(args.input)
    if not target.is_file():
        print(f"错误：文件不存在 -> {target}", file=sys.stderr)
        return 2

    report = audit_video(
        target,
        expected_aspect=args.expected_aspect,
        expected_fps=args.expected_fps,
        check_loudness=not args.no_loudness,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        m = report["media"]
        print(f"=== 视频体检结果: {report['status']} ===")
        print(
            f"画面: {m['width']}x{m['height']} @ {m['fps']}fps | codec={m['video_codec']} | "
            f"pix_fmt={m['pix_fmt']} | faststart={m['faststart']} | 时长={m['duration_sec']}s"
        )
        if m["has_audio"]:
            ld = report["loudness"]
            print(
                f"音频: codec={m['audio_codec']} | {m['sample_rate']}Hz | ch={m['channels']} | "
                f"I={ld.get('integrated_lufs')} LUFS | TP={ld.get('true_peak_dbtp')} dBTP"
            )
        else:
            print("音频: 无音轨")
        if report["black_segments"]:
            print(f"黑帧区间: {report['black_segments']}")
        if report["issues"]:
            print("\n[硬伤 Issues]")
            for item in report["issues"]:
                print(f"  - {item}")
        if report["warnings"]:
            print("\n[提示 Warnings]")
            for item in report["warnings"]:
                print(f"  - {item}")

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
