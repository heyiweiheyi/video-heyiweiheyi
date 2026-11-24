# `video-heyiweiheyi` — 交互式高阶视频制作 Agent Skill

遵循 [Agent Skills (`agentskills.io`)](https://agentskills.io) 开放标准的个人视频制作总控技能（别名：`video_heyiweiheyi`），全面兼容 **Antigravity、Claude Code、OpenAI Codex、Cursor、Windsurf、Gemini CLI** 等主流 AI Agent 工具。

---

## 核心设计理念：三层解耦 + 交互向导

1. **显性可选菜单 ①：段落公式化模板库（`recipes/`）**
   - 存放占据独立时间轴的标志性画面玩法（如 `回忆快闪`），在交互向导的 **开头（单选） / 中间（多选 + 重复度追问） / 结尾（单选）** 三个环节全部完整列出，不隐藏。
   - 若模板带有 `suggested_section`，展示为 `<display_name>（<suggested_section>）`；未指定时直接展示 `<display_name>`。

2. **显性可选菜单 ②：独立转场效果库（`transitions/`）**
   - 存放出入场与片段交界处的转场/叠影手法，在选完段落模板后通过**独立「转场选择界面」**多选配置，与段落模板彻底解耦、互不混杂。

3. **隐性静默底座：底层通用视频规范（`foundations/`）**
   - 不进入交互菜单，全程静默生效：
     - **第 0 步全局规格**：`16:9` / `9:16` 画幅与平台安全区（防抖音/B站 UI 遮挡字幕）+ 声音模式（纯 BGM / 配音闪避）
     - **多引擎分段 + FFmpeg 统一总装**：支持 `python-pil-ffmpeg` / `ffmpeg` / `remotion` / `manim` 引擎声明与优雅降级，所有段落标准化后由 `assemble_timeline.py` 统一拼接
     - **Audio-First + 分镜表确认**：配音驱动时间轴、正式渲染前输出分镜时长与转场确认表
     - **素材获取 + 无网/无实拍视频降级**：支持「自备 / 联网找 / 去画生成」；无联网能力时强制切换为「去画/生成」；缺少实拍视频时自动降级为「生图 + Ken Burns 运镜」
     - **双维自动化验收闭环**：内置 `probe_video.py`（H.264 `yuv420p`、`faststart`、LUFS 响度、黑帧体检）与 `extract_keyframes.py`（带安全区参考线的关键帧联系表 Contact Sheet PNG 目检）

---

## 当前已收录模板与转场

### 段落公式化模板（`recipes/catalog.json`）

| ID | 选项展示名 | 建议位置 | 典型时长 | 核心说明 |
| :--- | :--- | :---: | :---: | :--- |
| `memory-flashback` | `回忆快闪` | — | `2–8s` | 双轨半步（`0.15s`）交错叠化走马灯：单图 `0.3s` + 不透明度三关键帧 `0%→100%→0%` + 动感缩小与轻度缩放模糊，需提供多张回忆图片 |
| `split-screen-beat-flash` | `六分屏闪白卡点` | — | `4–14s` | 6 等分竖条百叶窗分屏卡点：随节拍逐格点亮首图并波浪式逐格切换多张图片，每格片头/片尾 3 帧亮度+对比度拉满闪白脉冲（支持自动 BGM 波峰卡点） |

### 独立转场效果（`transitions/catalog.json`）

| ID | 选项展示名 | 建议位置 | 典型时长 | 核心说明 |
| :--- | :--- | :---: | :---: | :--- |
| `fade-in-out` | `逐渐显现/消失（建议出入场）` | 建议出入场 | `1.5s` | 单轨不透明度关键帧 `0%→100%` 淡入 / `100%→0%` 淡出（可选音频同步淡化） |
| `seamless-cross-dissolve` | `无缝衔接转场（建议镜头间）` | 建议镜头间 | `1.2s` | 两段素材画中画重叠，不透明度 `0%→100%` 丝滑交叉叠化 + 音轨交叉淡化 |
| `ghost-double-exposure` | `电影感若隐若现` | — | `3.0s` | 画中画叠轨三关键帧 `0%→50%→0%` 双重曝光浮影，半透明交织后缓缓消散 |

---

## 仓库目录结构

```text
video-heyiweiheyi/
├── .agents/
│   └── skills.json                                        # Antigravity 自动发现配置
├── skills/
│   └── video-heyiweiheyi/
│       ├── SKILL.md                                       # 轻量总控：第0步规格 + 四步向导(含转场选择) + 素材/离线降级 + 分镜确认
│       ├── recipes/                                       # 显性可选 ①：段落/画面公式化模板库
│       │   ├── catalog.json
│       │   ├── memory-flashback/
│       │   │   ├── RECIPE.md
│       │   │   ├── references/jianying-and-ffmpeg-manual.md
│       │   │   └── scripts/build_memory_flashback.py
│       │   └── split-screen-beat-flash/
│       │       ├── RECIPE.md
│       │       ├── references/jianying-and-ffmpeg-manual.md
│       │       └── scripts/build_split_screen_beat_flash.py
│       ├── transitions/                                   # 显性可选 ②：独立转场效果库
│       │   ├── catalog.json
│       │   ├── fade-in-out/
│       │   │   ├── TRANSITION.md
│       │   │   ├── references/jianying-and-ffmpeg-manual.md
│       │   │   └── scripts/apply_fade_in_out.py
│       │   ├── seamless-cross-dissolve/
│       │   │   ├── TRANSITION.md
│       │   │   ├── references/jianying-and-ffmpeg-manual.md
│       │   │   └── scripts/apply_seamless_dissolve.py
│       │   └── ghost-double-exposure/
│       │       ├── TRANSITION.md
│       │       ├── references/jianying-and-ffmpeg-manual.md
│       │       └── scripts/apply_ghost_double_exposure.py
│       └── foundations/                                   # 隐性常驻：底层通用视频制作规范与工具脚本
│           ├── video-foundations.md
│           └── scripts/
│               ├── ffmpeg_utils.py
│               ├── probe_video.py
│               ├── extract_keyframes.py
│               └── assemble_timeline.py
├── .gitignore
└── README.md
```

---

## 跨 Agent 工具安装与使用

### 方式 1：通用 Skills CLI（支持 Claude Code / Codex / Cursor / Antigravity 等）
```bash
npx skills add heyiweiheyi/video-heyiweiheyi
```

### 方式 2：Google Antigravity 全局挂载
克隆仓库后，在 `~/.gemini/config/skills.json` 的 `entries` 数组中追加：
```json
{
  "entries": [
    {
      "path": "~/.gemini/antigravity/scratch/ppt-heyiweiheyi/skills"
    },
    {
      "path": "~/.gemini/antigravity/scratch/video-heyiweiheyi/skills"
    }
  ]
}
```

### 方式 3：Claude Code / Cursor / Codex 手动安装
将仓库中的 `skills/video-heyiweiheyi/` 整个目录复制到对应工具的技能目录即可：
- **Claude Code**：`~/.claude/skills/video-heyiweiheyi/` 或 `<项目>/.claude/skills/video-heyiweiheyi/`
- **OpenAI Codex**：`~/.agents/skills/video-heyiweiheyi/` 或 `<项目>/.agents/skills/video-heyiweiheyi/`
- **Cursor**：`<项目>/.cursor/skills/video-heyiweiheyi/`

---

## 后续扩展指南

- **添加新段落模板（进开头/中间/结尾选项）**：在 `skills/video-heyiweiheyi/recipes/<new-id>/` 创建 `RECIPE.md`、`references/`、`scripts/`，并在 `recipes/catalog.json` 追加元数据即可。
- **添加新转场效果（进转场选择界面）**：在 `skills/video-heyiweiheyi/transitions/<new-id>/` 创建 `TRANSITION.md`、`references/`、`scripts/`，并在 `transitions/catalog.json` 追加元数据即可。
- **沉淀底层通用规范（不进选项，静默生效）**：直接补充至 `skills/video-heyiweiheyi/foundations/video-foundations.md`。
