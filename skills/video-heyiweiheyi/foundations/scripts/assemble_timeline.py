#!/usr/bin/env python3
"""Unified FFmpeg timeline assembler for video-heyiweiheyi.

Normalizes all segment clips to a uniform resolution/fps/audio spec, chains transitions
between segments (cut / seamless-cross-dissolve), applies optional opening/closing fades
(fade-in-out), mixes optional BGM + voiceover with automatic ducking, and exports
H.264 yuv420p + AAC 48kHz + faststart MP4.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ffmpeg_utils import get_ffmpeg_exe, normalize_clip, probe_media_info


def assemble_timeline(
    clips: list[str | Path],
    output_path: str | Path,
    aspect: str = "16:9",
    fps: int = 30,
    fit_mode: str = "cover",
    transition: str = "seamless-cross-dissolve",
    transition_dur: float = 1.0,
    fade_in: float = 0.0,
    fade_out: float = 0.0,
    bgm_path: str | Path | None = None,
    bgm_volume_db: float = -8.0,
    voiceover_path: str | Path | None = None,
    normalize_lufs: bool = True,
    target_lufs: float = -14.0,
    crf: int = 18,
) -> Path:
    if not clips:
        raise ValueError("clips 列表不能为空。")

    ffmpeg = get_ffmpeg_exe()
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        norm_clips: list[Path] = []
        durations: list[float] = []
        for idx, clip in enumerate(clips):
            nc = tmp / f"seg_{idx:03d}.mp4"
            normalize_clip(clip, nc, aspect=aspect, fps=fps, fit_mode=fit_mode, crf=crf)
            info = probe_media_info(nc)
            dur = info["duration_sec"] or 1.0
            norm_clips.append(nc)
            durations.append(dur)

        # Step 1: Chain segments
        merged_video = tmp / "merged.mp4"
        if len(norm_clips) == 1:
            merged_video = norm_clips[0]
            total_dur = durations[0]
        elif transition == "cut" or transition_dur <= 0:
            concat_file = tmp / "concat.txt"
            concat_file.write_text(
                "\n".join(f"file '{p.as_posix()}'" for p in norm_clips),
                encoding="utf-8",
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_file),
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
                    str(merged_video),
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            total_dur = sum(durations)
        else:
            # Chain xfade + acrossfade iteratively across all clips
            cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error"]
            for nc in norm_clips:
                cmd += ["-i", str(nc)]

            vf_parts: list[str] = []
            af_parts: list[str] = []
            prev_v = "[0:v]"
            prev_a = "[0:a]"
            running_dur = durations[0]

            for i in range(1, len(norm_clips)):
                td = min(transition_dur, running_dur * 0.45, durations[i] * 0.45)
                offset = max(0.0, running_dur - td)
                out_v = f"[v{i}]"
                out_a = f"[a{i}]"
                vf_parts.append(
                    f"{prev_v}[{i}:v]xfade=transition=fade:duration={td:.3f}:offset={offset:.3f}{out_v}"
                )
                af_parts.append(f"{prev_a}[{i}:a]acrossfade=d={td:.3f}:c1=tri:c2=tri{out_a}")
                prev_v = out_v
                prev_a = out_a
                running_dur = offset + durations[i]

            total_dur = running_dur
            filter_complex = ";".join(vf_parts + af_parts)
            cmd += [
                "-filter_complex",
                filter_complex,
                "-map",
                prev_v,
                "-map",
                prev_a,
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
                str(merged_video),
            ]
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res.returncode != 0:
                raise RuntimeError(f"转场拼接失败: {res.stderr}")

        # Step 2: Optional fade-in/fade-out + BGM/Voiceover mixing + LUFS normalization
        cmd = [ffmpeg, "-y", "-hide_banner", "-loglevel", "error", "-i", str(merged_video)]
        input_idx = 1
        vo_idx = None
        bgm_idx = None
        if voiceover_path:
            cmd += ["-i", str(voiceover_path)]
            vo_idx = input_idx
            input_idx += 1
        if bgm_path:
            cmd += ["-stream_loop", "-1", "-i", str(bgm_path)]
            bgm_idx = input_idx
            input_idx += 1

        vf_chain = []
        if fade_in > 0:
            vf_chain.append(f"fade=t=in:st=0:d={fade_in:.3f}")
        if fade_out > 0 and total_dur > fade_out:
            vf_chain.append(f"fade=t=out:st={total_dur - fade_out:.3f}:d={fade_out:.3f}")
        vf_str = ",".join(vf_chain) if vf_chain else "null"

        af_blocks: list[str] = []
        audio_out_label = "[0:a]"

        if vo_idx is not None and bgm_idx is not None:
            # Voiceover + BGM sidechain ducking
            bgm_fade_out_st = max(0.0, total_dur - 1.5)
            af_blocks.append(
                f"[{vo_idx}:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[vo_mix][vo_sc]"
            )
            af_blocks.append(
                f"[{bgm_idx}:a]atrim=0:{total_dur:.3f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo,"
                f"volume={bgm_volume_db}dB,"
                f"afade=t=in:st=0:d=0.8,afade=t=out:st={bgm_fade_out_st:.3f}:d=1.5[bgm_prep]"
            )
            af_blocks.append(
                "[bgm_prep][vo_sc]sidechaincompress=threshold=0.02:ratio=6:attack=30:release=350[bgm_ducked]"
            )
            af_blocks.append(
                "[0:a][vo_mix][bgm_ducked]amix=inputs=3:duration=first:normalize=0[amixed]"
            )
            audio_out_label = "[amixed]"
        elif bgm_idx is not None:
            bgm_fade_out_st = max(0.0, total_dur - 1.5)
            af_blocks.append(
                f"[{bgm_idx}:a]atrim=0:{total_dur:.3f},asetpts=PTS-STARTPTS,"
                f"aresample=48000,aformat=channel_layouts=stereo,"
                f"volume={bgm_volume_db}dB,"
                f"afade=t=in:st=0:d=0.8,afade=t=out:st={bgm_fade_out_st:.3f}:d=1.5[bgm_prep]"
            )
            af_blocks.append("[0:a][bgm_prep]amix=inputs=2:duration=first:normalize=0[amixed]")
            audio_out_label = "[amixed]"
        elif vo_idx is not None:
            af_blocks.append(
                f"[{vo_idx}:a]aresample=48000,aformat=channel_layouts=stereo[vo_prep]"
            )
            af_blocks.append("[0:a][vo_prep]amix=inputs=2:duration=first:normalize=0[amixed]")
            audio_out_label = "[amixed]"

        if normalize_lufs and (bgm_idx is not None or vo_idx is not None):
            af_blocks.append(
                f"{audio_out_label}loudnorm=I={target_lufs}:TP=-1.0:LRA=11[afinal]"
            )
            audio_out_label = "[afinal]"

        filter_complex_parts = [f"[0:v]{vf_str}[vfinal]"] + af_blocks
        cmd += [
            "-filter_complex",
            ";".join(filter_complex_parts),
            "-map",
            "[vfinal]",
            "-map",
            audio_out_label,
            "-t",
            f"{total_dur:.3f}",
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
            raise RuntimeError(f"总装封装失败: {res.stderr}")

    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="video-heyiweiheyi 多段落统一总装脚本")
    parser.add_argument("--clips", nargs="+", required=True, help="按顺序输入的视频片段列表")
    parser.add_argument("--output", required=True, help="最终成片输出路径 (.mp4)")
    parser.add_argument("--aspect", default="16:9", help="目标画幅 (16:9 / 9:16 / 1:1)")
    parser.add_argument("--fps", type=int, default=30, help="统一帧率 (默认 30)")
    parser.add_argument("--fit-mode", choices=["cover", "blur_fit"], default="cover", help="画幅适配方式")
    parser.add_argument(
        "--transition",
        choices=["cut", "seamless-cross-dissolve"],
        default="seamless-cross-dissolve",
        help="片段间默认衔接方式",
    )
    parser.add_argument("--transition-dur", type=float, default=1.0, help="转场重叠时长（秒）")
    parser.add_argument("--fade-in", type=float, default=0.0, help="片头黑场渐显时长（秒）")
    parser.add_argument("--fade-out", type=float, default=0.0, help="片尾黑场渐隐时长（秒）")
    parser.add_argument("--bgm", default=None, help="可选：BGM 音频路径")
    parser.add_argument("--bgm-volume-db", type=float, default=-8.0, help="BGM 基础增益 dB（默认 -8）")
    parser.add_argument("--voiceover", default=None, help="可选：旁白人声音频路径（自动触发 BGM 闪避）")
    parser.add_argument("--no-loudnorm", action="store_true", help="跳过 LUFS 响度归一化")
    args = parser.parse_args()

    out = assemble_timeline(
        clips=args.clips,
        output_path=args.output,
        aspect=args.aspect,
        fps=args.fps,
        fit_mode=args.fit_mode,
        transition=args.transition,
        transition_dur=args.transition_dur,
        fade_in=args.fade_in,
        fade_out=args.fade_out,
        bgm_path=args.bgm,
        bgm_volume_db=args.bgm_volume_db,
        voiceover_path=args.voiceover,
        normalize_lufs=not args.no_loudnorm,
    )
    print(f"总装完成: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
