---
name: video-heyiweiheyi
description: >-
  Personal interactive video design, editing & production suite (alias: video_heyiweiheyi).
  Guides the user through a cross-agent interactive wizard covering global video specs (16:9 / 9:16
  aspect ratio & audio mode), formulaic segment recipes for Opening (开头), Middle (中间, multi-select
  with repeat-avoidance control), and Closing (结尾), a dedicated Transition selector (转场选择),
  structured media/script collection with offline-safe AI generation fallback, and a storyboard timeline
  confirmation before rendering — while silently enforcing foundational encoding (H.264 yuv420p + faststart),
  audio-first sync, LUFS loudness normalization & voiceover ducking, platform safe zones, multi-engine
  assembly, and automated probe + keyframe contact-sheet verification. Use whenever the user invokes
  video-heyiweiheyi / video_heyiweiheyi or asks to design, edit, synthesize, or polish a video.
---

# `video-heyiweiheyi` — 交互式视频制作总控技能

> **兼容性标识**：本技能遵循 [Agent Skills (`agentskills.io`)](https://agentskills.io) 开放标准，目录名与 `name` 统一为 `video-heyiweiheyi`（触发别名 `video_heyiweiheyi`），全面兼容 Antigravity、Claude Code、OpenAI Codex、Cursor、Windsurf、Gemini CLI 等主流 AI Agent 工具。

---

## 0. 核心分层原则（严禁混淆）

本技能由三个职责清晰、严格隔离的层次构成（两套显性可选菜单 + 一套隐性常驻底座）：

1. **显性可选 ①：段落/画面公式化模板库（`./recipes/`）**
   - 存放占据独立时间轴段落、具有标志性视觉玩法的视频模板（如 `回忆快闪` 等），负责决定**每一段播什么画面**。
   - **唯一菜单来源**：运行时必须先读取 [`./recipes/catalog.json`](./recipes/catalog.json)，动态生成「开头 / 中间 / 结尾」选项。
   - **全局可见 + 括号建议规则**：
     - `recipes/catalog.json` 中的**全部模板**都必须在「开头」「中间」「结尾」三个环节的选项中完整列出，绝不因建议位置或默认画幅而隐藏。
     - 若某模板的 `suggested_section` 非空（如 `"建议开头"`、`"建议中间"`、`"建议结尾"`），展示格式必须为 **`<display_name>（<suggested_section>）`**；若为空字符串 `""`，则直接展示 **`<display_name>`**，不加括号。
2. **显性可选 ②：独立转场效果库（`./transitions/`）**
   - 存放片头入场、片段之间衔接及片尾退场的转场/叠影手法（如 `逐渐显现/消失`、`无缝衔接转场`、`电影感若隐若现` 等），负责决定**段与段怎么过渡**。
   - **唯一菜单来源**：运行时读取 [`./transitions/catalog.json`](./transitions/catalog.json)，在专属的「转场选择界面」中供用户多选；同样遵循括号建议规则（`suggested_position` 非空时拼为 `<display_name>（<suggested_position>）`，为空则直接展示 `<display_name>`）。
3. **隐性常驻：底层通用视频功底（`./foundations/`）**
   - 存放每一段视频都应默认遵守的基础规范：画幅与平台安全区（16:9 / 9:16 抖音/B站防遮挡）、帧率统一（30/60fps）、编码兼容（H.264 `yuv420p` + AAC `48kHz` + `faststart`）、Audio-First 音画同步与节拍对齐、BGM 响度归一化（LUFS）与人声闪避（Ducking）、编辑保护防覆盖、多引擎分段统一总装，以及探针体检 + 关键帧联系表目检闭环（详见 [`./foundations/video-foundations.md`](./foundations/video-foundations.md)）。
   - **严禁把底层通用规范放进交互选项菜单**——它们必须在整条视频制作中全程静默生效。

---

## 1. 运行时交互向导协议（Dual-Mode Cross-Agent Wizard）

当本技能被触发用于策划、剪辑或生成视频时，**不要直接跳过询问就开始渲染**，必须先按顺序完成以下交互选择。

### 双模式交互兼容规范
- **模式 A（支持原生交互选择器的 Agent，如 Antigravity `ask_question` / Claude Code `AskUserQuestion`）**：优先使用原生单选/多选交互卡片收集用户选择（可将「第 0 步：全局规格」与「第 1 步：开头模式」合并在同一轮卡片中，减少打扰）。
- **模式 B（纯文本对话 Agent，如 Codex CLI / Cursor Chat / 终端工具）**：自动降级为清晰的编号 Markdown 菜单，提示用户回复序号即可（如 `画幅选1，声音选1，开头选1，中间选2，结尾选2，转场选1和2`），确保零工具依赖、100% 跑通。

### 前置读取目录
启动向导前，同时读取：
- [`./recipes/catalog.json`](./recipes/catalog.json) → 拼装段落模板展示标签，并在每个环节末尾追加兜底项：**`自主设计（不套用固定公式）`**。
- [`./transitions/catalog.json`](./transitions/catalog.json) → 拼装转场效果展示标签，并在末尾追加兜底项：**`自主搭配（由 AI 按节奏决定硬切或基础衔接）`**。

---

### 第 0 步：全局规格确认（画幅 + 声音模式）
*(若用户首轮指令已明确给出画幅或声音模式，直接确认沿用，跳过重复提问。)*
1. **画幅规格（单选）**：
   - `16:9 横屏（1920×1080，B站 / YouTube / 汇报展示）`
   - `9:16 竖屏（1080×1920，抖音 / 视频号 / 小红书 / Reels）`
   - `其他规格（如 1:1 方形 / 4K，用户自定义）`
2. **声音驱动模式（单选）**：
   - `纯 BGM 画面流（卡点 / 混剪 / 氛围展示，无旁白配音）`
   - `配音旁白 + BGM 闪避（口播 / 解说 / 故事叙述，BGM 自动压低避让人声）`

---

### 第 1 步：开头模式（单选）
- **提示语**：`开头：请选择你要的开头模式：`
- **选项**：`recipes/catalog.json` 全部模板（按规则带/不带建议括号） + `自主设计（不套用固定公式）`

---

### 第 2 步：中间要用到（多选 + 重复度追问）
- **提示语**：`中间要用到：（可多选）`
- **选项**：`recipes/catalog.json` 全部模板（按规则带/不带建议括号） + `自主设计（不套用固定公式）`
- **条件必问追问（只要用户在中间至少选了 1 个公式化模板就必须追问）**：
  - **问题**：`是否介意在中间这么多片段/章节里多次用到所选模板？`
  - **选项 1（介意重复）**：`是，介意重复（每个所选模板在中间最多使用 1 次；其余超出段落由 AI 运用底层视频功底自主设计）`
  - **选项 2（不介意重复）**：`否，不介意重复（允许在中间按节奏合理复用，并做构图/配色/运镜微调防视觉疲劳）`

---

### 第 3 步：结尾模式（单选）
- **提示语**：`结尾用：请选择你要的结尾模式：`
- **选项**：`recipes/catalog.json` 全部模板（按规则带/不带建议括号） + `自主设计（不套用固定公式）`

---

### 第 3.5 步：转场效果选择（独立转场界面，多选）
- **提示语**：`转场效果：请选择出入场及片段之间要使用的转场方式：（可多选）`
- **选项**：`transitions/catalog.json` 全部转场效果（按规则带/不带建议括号） + `自主搭配（由 AI 按节奏决定硬切或基础衔接）`
- *(注：如果选了多种转场，将在第 5 步分镜表中逐一标明每个接缝具体使用的转场，防止全局胡乱堆叠。)*

---

### 第 4 步：按所选模板收集所需素材与文案（支持不提供 + 无网降级 + 无实拍视频降级）
选完「全局规格 / 开头 / 中间 / 结尾 / 转场」后、**正式生成任何视频前**，遍历所有被选中的段落模板（以及需要额外叠加画面的转场，如 `电影感若隐若现`），读取 `catalog.json` 中声明的 `required_inputs`（结构含 `key / label / type / required / allow_ai_generate / description`），主动询问素材与文案：

1. **自动去重**：用户在之前对话中已提供的图片、视频、音频、标题或文案直接确认沿用，**不重复索要**。
2. **分环节列单 + 明确给出获取方式**：按「开头 / 中间 / 结尾 / 转场 / 全局音轨」分组列出缺失的 `[必填]` / `[可选]` 项：
   - **视觉类素材（`image` / `image_list` / `video` / `video_or_image`）**，明确提供三种选择（双模式兼容）：
     - **① 我自己提供**：用户直接上传或提供本地路径/文件夹路径。
     - **② 根据主题联网找**：Agent 调用联网搜索/浏览器工具检索高清、无水印、匹配当前画幅比例（16:9 或 9:16）的免版权图片或短视频素材。
     - **③ 根据主题去画（或生成）**：Agent 调用图像/视频生成工具按主题与画幅比例生成素材。
   - **离线降级硬规（跨 Agent 兼容关键）**：
     - 发起询问前必须先检测当前 Agent 是否具备联网能力（有无 Web Search / Browser / 联网 MCP 或处于无网沙盒）。
     - **没有联网功能时只能去画/生成**：选项中自动隐藏「② 根据主题联网找」，仅提供「① 我自己提供」与「③ 根据主题去画（或生成）」；若用户仍口头要求联网找，须礼貌说明当前工具不支持联网，并自动切换为「根据主题去画（或生成）」。
     - 若**既无联网能力、又无 AI 生图/生视频工具**（如纯离线代码终端）：对氛围抽象背景/图形动效可用 Python (`Pillow`/`numpy`) 程序化绘制；若模板强依赖写实人物/真实回忆照片（如用户专属相册版 `回忆快闪`），明确说明环境限制，请用户提供本地素材路径。
   - **无实拍视频优雅降级（针对 `video` / `video_or_image`）**：
     - 当模板需要视频素材而用户未自备、且当前环境无网或无视频生成模型时，**自动降级为「按主题生图 + Ken Burns 缓慢推拉/平移/视差运镜」**（调用 [`./foundations/scripts/ffmpeg_utils.py`](./foundations/scripts/ffmpeg_utils.py) 内置 Ken Burns 转换器）生成平滑动态镜头，并在确认时明确告知用户。
   - **音频与文案类素材（`audio_bgm` / `audio_voiceover` / `audio_sfx` / `subtitle_text` / `text` / `text_list`）**：
     - 文案类允许用户自行提供或授权 AI 根据主题代拟；但 **`allow_ai_generate: false`** 的真实个人信息、署名落款、真实业务数据严禁编造（未提供时留空或置占位提示）。
     - 旁白配音允许用户提供录音或指定 AI TTS；BGM 允许用户提供本地音频或联网检索免版权音乐（无网且无音乐生成工具时，可提示用户提供本地 BGM 或默认输出无 BGM 纯画质成片待用户配乐）。
3. **等待确认后再执行**：必须等用户提供素材或明确授权获取方式后，再进入分镜确认与制作。

---

### 第 5 步：分镜时长与转场确认表（正式渲染前轻量检查点）
由于视频渲染成本高于静态文件，在正式渲染整片前，先向用户输出一张极简**分镜与时间轴确认表**：

| 序号 | 环节 | 选用模板 | 预计时长 | 画面/素材来源 | 文案/字幕 | 衔接转场 | 音频/BGM 节点 |
| :---: | :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| 1 | 开头 | 例：`回忆快闪` | `4.5s` | 用户 28 张照片 | 主标题 | 入场：`逐渐显现` | 鼓点渐起 |
| 2 | 中间 | 例：自主设计 | `8.0s` | 主题生图 + 推镜 | 旁白/字幕 | 切入：`无缝衔接转场` | 人声主轨 + BGM 闪避 |
| 3 | 结尾 | 例：自主设计 | `3.5s` | 氛围图 | 致谢落款 | 叠影：`电影感若隐若现` → `逐渐消失` | 音乐淡出 |

- 若处于「配音旁白模式」，先执行 **Audio-First**：探针测算旁白音频精确时长后再反推上表中的每段时长。
- 用户确认分镜表（或给出微调意见）后，立即进入全自动制作与验收交付。

---

## 2. 按需加载、分段多引擎渲染与验收流程（Progressive Disclosure）

1. **按需加载选中模块**：
   - 仅读取用户选中的 `./recipes/<id>/RECIPE.md` 与 `./transitions/<id>/TRANSITION.md`（及其 `references/` 与 `scripts/`），未选中的模块无需读取，保持上下文精简。
2. **全程注入底层通用规范**：
   - 编写或执行任何视频脚本前，务必阅读并遵守 [`./foundations/video-foundations.md`](./foundations/video-foundations.md) 的全部硬性规范。
3. **多引擎分段渲染 + FFmpeg 统一总装**：
   - 读取 `catalog.json` 中的 `engine` 与 `fallback_engine`（支持 `python-pil-ffmpeg` / `ffmpeg` / `remotion` / `manim`）；若首选引擎在当前机器不可用（如无 Node/Remotion），自动平滑回退到 `fallback_engine` 并告知用户。
   - 每个段落独立输出标准化中间片（统一分辨率、统一帧率、统一像素格式 `yuv420p`、统一采样率 `48kHz`，并按需预留转场重叠帧 handles）。
   - 使用 [`./foundations/scripts/assemble_timeline.py`](./foundations/scripts/assemble_timeline.py) 或等效 FFmpeg 滤镜管线完成转场串联、BGM 响度归一化（LUFS）、人声闪避（Ducking）与 `faststart` 封装。
4. **必做双维验收闭环（严禁盲交成片）**：
   - **硬指标体检**：运行 [`./foundations/scripts/probe_video.py`](./foundations/scripts/probe_video.py) 校验 `h264` + `yuv420p` + `faststart`、分辨率/帧率一致性、音画时长漂移（`< 0.05s`）、综合响度（`-14 ~ -16 LUFS`）与首尾黑帧/静音。
   - **视觉抽帧目检**：运行 [`./foundations/scripts/extract_keyframes.py`](./foundations/scripts/extract_keyframes.py) 生成带时间戳与 **16:9 / 9:16 平台安全区参考线** 的关键帧联系表（Contact Sheet PNG），直接用看图工具目检字幕安全区、画面裁切、叠影比例与转场衔接无异常后再交付。

---

## 3. 后续如何扩展本技能库

- **新增段落模板（进「开头 / 中间 / 结尾」菜单）**：
  1. 在 `./recipes/<new-id>/` 下创建 `RECIPE.md`、`references/` 与 `scripts/`。
  2. 在 [`./recipes/catalog.json`](./recipes/catalog.json) 追加一条记录（含 `id`、`display_name`、`suggested_section`、`supported_aspects`、`duration_range_sec`、`audio_sync`、`engine`、`fallback_engine`、`required_inputs` 及文档/脚本路径）。
- **新增转场效果（进独立「转场选择」菜单）**：
  1. 在 `./transitions/<new-id>/` 下创建 `TRANSITION.md`、`references/` 与 `scripts/`。
  2. 在 [`./transitions/catalog.json`](./transitions/catalog.json) 追加一条记录。
- **沉淀底层通用规范（不进选项，全局静默生效）**：
  - 直接补充至 [`./foundations/video-foundations.md`](./foundations/video-foundations.md)。
