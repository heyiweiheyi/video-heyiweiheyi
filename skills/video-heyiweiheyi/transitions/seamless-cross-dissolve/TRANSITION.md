# Transition: 无缝衔接转场 (`seamless-cross-dissolve`)

> **展示名称**：`无缝衔接转场（建议镜头间）`  
> **典型重叠时长**：`0.8s – 2.0s`（默认 `1.2s`）  
> **适用位置**：任意两段相邻视频片段之间的平滑过渡

将后一段素材切入画中画并与前一段尾部重叠，在重叠区间内令后段画面不透明度由 `0% → 100%` 平滑上升（Cross-Dissolve），同步对音轨做等距交叉淡化（`acrossfade`），消除硬切跳跃感。

---

## 核心参数与自动化脚本

调用 [`scripts/apply_seamless_dissolve.py`](./scripts/apply_seamless_dissolve.py)：

```bash
python skills/video-heyiweiheyi/transitions/seamless-cross-dissolve/scripts/apply_seamless_dissolve.py \
  --clip-a clip1.mp4 \
  --clip-b clip2.mp4 \
  --output joined.mp4 \
  --duration 1.2 \
  --aspect 16:9 \
  --fps 30
```

- 脚本会自动将 `clip-a` 与 `clip-b` 标准化至相同的分辨率、帧率与 `48kHz` 立体声音轨，再执行精确重叠交叉叠化，杜绝分辨率或帧率不一致导致的 FFmpeg `xfade` 报错。
- 剪映手动复刻与 FFmpeg 滤镜对照详见 [`references/jianying-and-ffmpeg-manual.md`](./references/jianying-and-ffmpeg-manual.md)。
