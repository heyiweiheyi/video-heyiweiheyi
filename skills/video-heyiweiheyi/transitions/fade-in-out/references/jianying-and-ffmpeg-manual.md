# 「逐渐显现/消失」剪映手动步骤 & FFmpeg 参数对照

## 一、剪映（CapCut）手动步骤

1. **逐渐显现（淡入）**：
   - 导入视频素材，将播放头停在**开头（`00:00`）**，打上关键帧，找到 **「不透明度」** 调为 **`0`**。
   - 时间线后移约 `1.5s – 2.0s`，将不透明度调回 **`100`**（自动生成第二个关键帧）。
2. **逐渐消失（淡出）**：
   - 反向操作：在距离片尾 `1.5s – 2.0s` 处打关键帧（不透明度 `100`），移至片尾最后一帧将不透明度调为 **`0`**。

## 二、FFmpeg 等效滤镜

```bash
# 假设视频总时长为 D 秒，淡入 fin 秒，淡出 fout 秒：
ffmpeg -i input.mp4 \
  -vf "fade=t=in:st=0:d=1.5,fade=t=out:st=D-1.5:d=1.5" \
  -af "afade=t=in:st=0:d=1.5,afade=t=out:st=D-1.5:d=1.5" \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart output.mp4
```
