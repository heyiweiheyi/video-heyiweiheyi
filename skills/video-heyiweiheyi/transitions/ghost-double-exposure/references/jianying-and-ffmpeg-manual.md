# 「电影感若隐若现」剪映手动步骤 & FFmpeg 参数对照

## 一、剪映（CapCut）手动步骤

1. 在「无缝衔接转场」两段视频叠轨（主轨 + 画中画）的基础上操作。
2. 选中画中画片段，在其**开头**打第 1 个关键帧，不透明度调为 **`0`**。
3. 时间线后移至浮影高潮中点（如 `+1.5s`），打第 2 个关键帧，将不透明度调到 **`50` 左右**（`45–55`），此时两段画面同屏半透明重叠。
4. 继续将时间线后移（如再 `+1.5s`），打第 3 个关键帧，将不透明度调回 **`0`**，完成「若隐若现」电影感双重曝光浮影。

## 二、FFmpeg 等效滤镜

```bash
# 设浮影起播时刻 start=0.8s，总持续时长 dur=3.0s（half=1.5s），峰值不透明度 peak=0.50：
ffmpeg -i base_norm.mp4 -i overlay_norm.mp4 \
  -filter_complex "\
    [1:v]trim=0:3.0,setpts=PTS-STARTPTS,format=rgba,\
    fade=t=in:st=0:d=1.5:alpha=1,\
    fade=t=out:st=1.5:d=1.5:alpha=1,\
    colorchannelmixer=aa=0.50,\
    setpts=PTS+0.8/TB[ov];\
    [0:v][ov]overlay=0:0:eof_action=pass:enable='between(t,0.8,3.8)',format=yuv420p[vout]" \
  -map "[vout]" -map 0:a \
  -c:v libx264 -crf 18 -pix_fmt yuv420p -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart output.mp4
```
