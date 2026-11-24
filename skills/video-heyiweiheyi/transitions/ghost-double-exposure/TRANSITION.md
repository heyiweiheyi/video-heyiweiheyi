# Transition: 电影感若隐若现 (`ghost-double-exposure`)

> **展示名称**：`电影感若隐若现`（可用于主画面情绪叠影、回忆闪回过渡或梦幻双重曝光氛围段）  
> **典型时长**：`2.5s – 5.0s`（默认 `3.0s`，前半段 `1.5s` 缓升至 `50%`，后半段 `1.5s` 缓降至 `0%`）  
> **核心特征**：画中画叠轨三关键帧 `0% → 50% → 0%`，让两段画面以半透明双重曝光方式短暂共存后自然消散

在底层主画面持续推进的过程中，上层画中画浮影画面从完全不可见（`0%`）缓缓浮现至半透明峰值（约 `50%`，两段画面清晰互见如梦境/回忆交织），再柔和退回到 `0%` 彻底消失，极富电影叙事张力。

---

## 核心参数与自动化脚本

调用 [`scripts/apply_ghost_double_exposure.py`](./scripts/apply_ghost_double_exposure.py)：

```bash
python skills/video-heyiweiheyi/transitions/ghost-double-exposure/scripts/apply_ghost_double_exposure.py \
  --base night_shore.mp4 \
  --overlay sunset_silhouette.mp4 \
  --output double_exposure.mp4 \
  --start 0.8 \
  --duration 3.2 \
  --peak-opacity 0.50 \
  --aspect 16:9 \
  --fps 30
```

- `--overlay` 既支持 `.mp4` 视频，也支持单张静态图片（脚本自动施加轻缓 Ken Burns 运镜后叠化，避免浮影僵硬不动）。
- `--peak-opacity` 默认 `0.50`（即剪映不透明度 `50`），暗底画面推荐 `0.45–0.55`，亮底画面推荐 `0.38–0.48`。
- 剪映手动复刻与 FFmpeg 滤镜对照详见 [`references/jianying-and-ffmpeg-manual.md`](./references/jianying-and-ffmpeg-manual.md)。
