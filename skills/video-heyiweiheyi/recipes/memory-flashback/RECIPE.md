# Formulaic Video Recipe: 回忆快闪 (`memory-flashback`)

> **展示名称**：`回忆快闪`（无固定位置限制，可用于震撼回忆开场、中段情绪高潮闪回，或片尾走马灯回顾）  
> **推荐时长**：`2.0s – 8.0s`（按公式 `总时长 = (N + 1) × (clip_duration / 2)` 计算，例如 20 张图 ≈ `3.15s`，40 张图 ≈ `6.15s`）  
> **支持画幅**：`16:9`（`1920×1080`）、`9:16`（`1080×1920`）、`1:1`（`1080×1080`）  
> **首选引擎**：`python-pil-ffmpeg`（Pillow + NumPy 逐帧直推 FFmpeg，零 Node 依赖、全平台稳定）

将一组连续照片/记忆画面（建议 8–40 张）转化为极具电影情绪张力的**无缝交叉叠化走马灯快闪**：
- 每张图片时长仅 **`0.3s`**，通过 **主轨 + 画中画双轨错位 `0.15s`（半个片段）** 交错叠加；
- 每张图片自带 **`0% → 100% → 0%` 不透明度三关键帧** + **「动感缩小」高速缓动缩进（含轻微缩放动感模糊）**；
- 在任意重叠帧中，上一张正从 `100% → 0%` 淡出，下一张同步从 `0% → 100%` 淡入，**两张透明度之和恒为 `100%`**，彻底消除生硬硬切与黑帧闪烁，呈现如记忆涌现般的丝滑冲击力。

---

## 一、核心时间轴与数学参数

| 参数项 | 默认值 | 视觉作用说明 |
| :--- | :---: | :--- |
| 单图时长 `clip_duration` | **`0.30 s`** | 30fps 下为 9 帧，60fps 下为 18 帧；节奏紧凑不拖沓 |
| 双轨错位步长 `stride` | **`0.15 s`**（`clip_duration / 2`） | 主轨放第 `1, 3, 5...` 张；画中画轨对齐主轨中点关键帧放第 `2, 4, 6...` 张 |
| 不透明度曲线 | `0.00s: 0%` → `0.15s: 100%` → `0.30s: 0%` | 与相邻轨互补叠化（`α_A + α_B = 1.0`），画面亮度稳定无黑洞 |
| 入场动效（动感缩小） | `1.32× → 1.00×`（Ease-Out Cubic） | 开场急速推进缩回正常尺寸，前 35% 附带轻度缩放动感模糊 |
| 首尾淡入/淡出 | 首图 `0→100%`（可设首帧即亮）、末图 `100%→0%` | 可直接衔接前序或后续转场（如 `逐渐显现/消失` 或 `无缝衔接转场`） |

---

## 二、必需素材核对（`required_inputs`）

执行本模板前，**必须确认图片组素材（`images`）来源**：
1. **优先由用户提供**：本地图片文件夹路径或多张图片路径（如旅游照片、项目历程截图、人物成长记录、剧照等）。
2. **用户选择不自备时**：严格按 `SKILL.md` 第 4 步离线降级协议执行（有网可按主题检索高清图，无网则用 AI 生图工具批量生成主题系列图）。
3. **素材数量不足时的处理**：若用户仅提供 3–6 张图但希望时长达到 4–6 秒，可经用户同意后适度放慢 `clip_duration`（如 `0.45s–0.60s`）或补充主题配图，切忌在未告知的情况下机械重复同一张图。

---

## 三、自动化生成脚本调用

运行 [`scripts/build_memory_flashback.py`](./scripts/build_memory_flashback.py)：

```bash
# 方式 1：传入整个图片文件夹（按文件名自然排序）
python skills/video-heyiweiheyi/recipes/memory-flashback/scripts/build_memory_flashback.py \
  --images-dir path/to/photos_folder \
  --output path/to/memory_flashback.mp4 \
  --aspect 16:9 \
  --fps 60 \
  --clip-duration 0.30 \
  --zoom-start 1.32 \
  --bgm path/to/bgm.mp3

# 方式 2：显式指定图片列表
python skills/video-heyiweiheyi/recipes/memory-flashback/scripts/build_memory_flashback.py \
  --images img1.jpg img2.jpg img3.jpg img4.jpg img5.jpg img6.jpg \
  --output path/to/memory_flashback_vertical.mp4 \
  --aspect 9:16 \
  --fps 30
```

- **帧率建议**：回忆快闪属于高速动态切换，如条件允许推荐 **`60 fps`**（每张图 18 帧，动感缩小极其顺滑）；普通成片亦完全兼容 **`30 fps`**。
- **画幅适配**：默认 `--fit-mode cover` 居中无黑边裁切；若图片包含重要边缘信息不想裁切，可传 `--fit-mode blur_fit`（高斯模糊暗底 + 居中完整原图）。
- **剪映手动步骤与参数对照**：详见 [`references/jianying-and-ffmpeg-manual.md`](./references/jianying-and-ffmpeg-manual.md)。

---

## 四、验收要点

1. 使用 `foundations/scripts/probe_video.py` 确认编码为 `h264` + `yuv420p` + `faststart`、目标分辨率与帧率准确。
2. 使用 `foundations/scripts/extract_keyframes.py` 抽帧目检：确认重叠过渡帧呈现柔和双图叠化且无黑边、无拉伸变形、无花屏。
