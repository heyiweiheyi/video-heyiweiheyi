# Transition: 逐渐显现/消失 (`fade-in-out`)

> **展示名称**：`逐渐显现/消失（建议出入场）`  
> **典型时长**：`1.0s – 2.0s`（默认 `1.5s`）  
> **适用位置**：片头黑场缓入、章节间暗场呼吸停顿、片尾黑场缓出

通过单轨不透明度关键帧，让画面由纯黑平稳浮现（`0% → 100%`）或在结尾柔和沉入黑场（`100% → 0%`），同步可选施加音频淡入/淡出，避免突兀切入或骤停断音。

---

## 核心参数与自动化脚本

调用 [`scripts/apply_fade_in_out.py`](./scripts/apply_fade_in_out.py)：

```bash
python skills/video-heyiweiheyi/transitions/fade-in-out/scripts/apply_fade_in_out.py \
  --input clip.mp4 \
  --output clip_faded.mp4 \
  --fade-in 1.5 \
  --fade-out 1.5 \
  --audio-fade
```

- 仅做片头逐渐显现：传 `--fade-in 1.5 --fade-out 0`。
- 仅做片尾逐渐消失：传 `--fade-in 0 --fade-out 1.5`。
- 剪映手动复刻与 FFmpeg 滤镜对照详见 [`references/jianying-and-ffmpeg-manual.md`](./references/jianying-and-ffmpeg-manual.md)。
