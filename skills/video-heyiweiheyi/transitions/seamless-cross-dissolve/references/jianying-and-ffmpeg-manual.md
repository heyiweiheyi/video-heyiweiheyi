# 「无缝衔接转场」剪映手动步骤 & FFmpeg 参数对照

## 一、剪映（CapCut）手动步骤

1. 导入两段视频素材（镜头 A 与镜头 B）。
2. 选中镜头 B，点击 **「切画中画」**，向左拖动使其开头与镜头 A 的尾部重叠约 `1.0s – 1.5s`。
3. 在画中画镜头 B 的**开头位置**打关键帧，将 **「不透明度」** 调为 **`0`**。
4. 时间线后移至镜头 A 结束处（重叠区末尾），将画中画不透明度调回 **`100`**，即可形成丝滑无缝叠化转场。

## 二、FFmpeg 等效滤镜

```bash
# 假设 clip_a 时长为 dur_a，重叠时长 td = 1.2s，offset = dur_a - td：
ffmpeg -i clip_a_norm.mp4 -i clip_b_norm.mp4 \
  -filter_complex "[0:v][1:v]xfade=transition=fade:duration=1.2:offset=OFFSET[v];[0:a][1:a]acrossfade=d=1.2:c1=tri:c2=tri[a]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart output.mp4
```
