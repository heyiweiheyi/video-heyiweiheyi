# Formulaic Video Recipe: 六分屏闪白卡点 (`split-screen-beat-flash`)

> **展示名称**：`六分屏闪白卡点`（无固定位置限制，适合强节奏卡点开场、中段风光/写真高光混剪，或片尾多图定格展示）  
> **推荐时长**：`4.0s – 14.0s`（按公式 `总拍数 = 图片数 × 分屏栏数 + 换图间隔拍数` 计算，例如 6 张图 × 6 栏 @ `0.25s/拍` 约 `9.8s`）  
> **支持画幅**：`16:9`（`1920×1080`）、`9:16`（`1080×1920`）、`1:1`（`1080×1080`）  
> **首选引擎**：`python-pil-ffmpeg`（Pillow + NumPy 逐帧直推 FFmpeg，支持自动 BGM 能量波峰卡点）

将一组精选图片（建议 4–8 张，如天空云海、旅行摄影、产品大片）切割为 **6 条等宽竖向百叶窗分屏栏**，严格踩在音乐节拍上完成极富律动感的逐格切换：
- **首图逐格点亮**：纯黑画布开场，随前 6 个节拍点按序点亮第 1 张图的 6 个竖条，直至拼出完整画面；
- **逐格波浪换图**：每逢后续节拍点，逐栏将旧图切片替换为下一张图的对应切片，新旧画面短暂交错并置如钢琴键波浪推演；
- **3 帧闪白爆发脉冲**：每一栏切片在**入场前 3 帧**（高亮过曝回落正常）及**被替换前的最后 3 帧**（正常急冲高亮过曝）同步触发「亮度 + 对比度拉满」闪白特效，赋予卡点清脆凌厉的视觉打击感。

---

## 一、核心视觉与节奏参数

| 参数项 | 默认值 | 视觉作用说明 |
| :--- | :---: | :--- |
| 分屏栏数 `num_strips` | **`6`** | 画布宽度均分 6 等分竖条，栏间保留 `3 px` 极细暗缝形成精致分屏窗格 |
| 点亮/替换顺序 `reveal_order` | **`center-out`** | 6 栏默认 `[2, 3, 1, 4, 0, 5]` 从中间向两侧展开；可选 `left-to-right`、`right-to-left`、`alternate`、`random` |
| 单格闪白帧数 `flash_frames` | **`3` 帧**（@30fps ≈ `0.10s`） | 还原剪映「片头后 3 帧 + 片尾前 3 帧关键帧，端帧亮度/对比度拉满」闪烁变化 |
| 节拍驱动方式 | `beat_interval = 0.25s` 或 `--auto-beats` | 支持传 `--bgm` + `--auto-beats` 自动检测音频波峰，或传 `--bpm` / `--beats` 精确卡点 |
| 满屏喘息拍 `hold_beats` | **`1` 拍** | 每张图 6 栏完整拼齐后停留 1 拍再开始替换下一张，节奏松弛有度 |

---

## 二、必需素材核对（`required_inputs`）

执行本模板前，**必须确认图片组素材（`images`）来源**：
1. **优先由用户提供**：4–8 张风格契合的高清图片路径或文件夹。
2. **用户选择不自备时**：严格遵循 `SKILL.md` 第 4 步离线降级规范（有网检索高清无水印图，无网则批量 AI 生图）。
3. **BGM 配合**：强烈建议提供节奏清晰的 BGM 音频，开启 `--auto-beats` 或按歌曲 BPM 设定节拍；未提供时自动按均匀节拍生成纯净画质片断供后续总装配乐。

---

## 三、自动化生成脚本调用

运行 [`scripts/build_split_screen_beat_flash.py`](./scripts/build_split_screen_beat_flash.py)：

```bash
# 方式 1：传入图片文件夹 + 自动按固定节拍（0.24s/拍）生成 16:9 成片
python skills/video-heyiweiheyi/recipes/split-screen-beat-flash/scripts/build_split_screen_beat_flash.py \
  --images-dir path/to/sky_photos \
  --output path/to/split_beat_flash.mp4 \
  --aspect 16:9 \
  --fps 30 \
  --strips 6 \
  --order center-out \
  --beat-interval 0.24 \
  --bgm path/to/beat_music.mp3

# 方式 2：开启 BGM 能量波峰自动卡点检测（9:16 竖屏）
python skills/video-heyiweiheyi/recipes/split-screen-beat-flash/scripts/build_split_screen_beat_flash.py \
  --images-dir path/to/photos \
  --output path/to/split_beat_vertical.mp4 \
  --aspect 9:16 \
  --bgm path/to/beat_music.mp3 \
  --auto-beats
```

- 剪映手动复刻步骤与参数数学公式详见 [`references/jianying-and-ffmpeg-manual.md`](./references/jianying-and-ffmpeg-manual.md)。

---

## 四、验收要点

1. 运行 `foundations/scripts/probe_video.py` 核对 `h264` + `yuv420p` + `faststart`、分辨率、帧率及 LUFS 响度。
2. 运行 `foundations/scripts/extract_keyframes.py` 抽帧目检：确认 6 等分微缝整齐、跨图切换过程中可见新旧画面分栏并置、切点处有清晰但不过度死白的闪白瞬间，且末图完整定格无黑边。
