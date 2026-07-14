# AI Film Pipeline

多智能体「虚拟剧组」管线：把剧本推进为结构化 **FilmBible**，终点是 **可直接投喂的最终提示词**（中英双成品）。**不调用视频 API。**

> **ProductionBrief = 创作意图** · **Orchestrator = 调度总指挥** · **TaskTicket = 派工单**  
> **Skill = 岗位手册** · **Knowledge = 规则库** · **FilmBible = 本片状态**  
> **交付物 = `outputs/<项目名>/` 出厂件**

## 工业化原则

| 原则 | 含义 |
|------|------|
| **合同驱动** | 上下游只读写 FilmBible 字段；禁止岗位自由聊天 |
| **标准件输出** | 四段结构固定；中英均为可投喂成品；自动换行 |
| **单段上限** | 用户选 **15 或 30 秒** = 单次生成天花板，**不是整片时长** |
| **时间轴分镜** | 段内写成 `0-2秒，…` / `3-12秒，…`；模型按时间轴表现；流程黑话不进正文 |
| **到底才拆段** | 只有累计塞不进上限，才开下一段生成（`generation_packages`） |
| **门禁质检** | Critic 查结构 / 对白覆盖 / 说话人 / 镜句绑定；无静默 stub 伪装成功 |
| **可度量** | `prompt_board` 文末：**电影最终时长** + 生成段数 + 成片预估 |
| **可交付** | 固定目录：`prompt_board.html`（复制按钮）+ `.md` + `clips/` + `assets/` |

## 给外来智能体（必读）

**本仓库不托管视频模型 API，也不替你决定怎么分工。**  
**方案 B 时：由你（外来智能体）自己创建隔离的、各司其职的子智能体——不是去找本仓库的 OpenAI Key。**

任何 Agent 来跑本项目时，先读 **[`AGENTS.md`](AGENTS.md)**，并 **先问用户二选一**：

| 方案 | 含义 |
|------|------|
| **A 单智能体全包** | 一个执行者按顺序干完全部岗位 |
| **B 多智能体分工** | 每岗一个独立 Agent，**只装自己的 Skill + 知识库**，互不共享手册；**调度者负责 spawn/派工/merge** |

独立包装清单：[`agents/registry.json`](agents/registry.json) · 说明：[`agents/README.md`](agents/README.md)

> Python CLI 的 dry-run / `OPENAI_*` 是可选本地工具。  
> **架构不等于「调了 `film-pipeline run`」**；架构 = Skill + 知识库 + FilmBible 合同 +（方案 B 时）隔离子 Agent。

## 架构

```text
你 / Producer
  → ProductionBrief（必选：15|30 秒、风格包、是否资产轨）
       ↓
Orchestrator（代码总指挥 · 唯一派工者）
  ├─ 主链 main
  │    dramaturg → dialogue → director → look
  │    → cinematography → timing → generator(prompt_writer) → critic
  └─ 资产旁路 assets（可选并行）
       asset：人物/道具/场景三视图提示词
       image_refs 可空，随时换图，不堵主链
```

```bash
film-pipeline org          # 组织架构
film-pipeline stages       # 岗位列表
```

### 15 / 30 秒：单次生成上限

跑流水线之前先选定（或 `--max-clip`）：

| 选项 | 含义 |
|------|------|
| **15 秒** | 短时长视频模型单段 cap |
| **30 秒** | 长时长视频模型单段 cap |

```bash
# 交互询问（推荐）
film-pipeline run --script ... --project demo

# 脚本 / CI
film-pipeline run --script ... --project demo --max-clip 15
film-pipeline run --script ... --project demo --max-clip 30
```

**时长规则（代码确定性）：**

```text
needed ≈ pre_roll + max(dialogue_sec, move_sec) + post_hold
连续镜头打包进 generation_packages（每包 ≤ max_clip）
段内：时间轴分镜（0–2秒 / 3–12秒 / …）
仅当单镜本身超 cap，或累计塞不下 → 开下一段生成
```

### 最终提示词从哪来？

`generator` 阶段由 **Prompt Writer**（`skills/prompt_writer`）根据 FilmBible **写可执行自然语言**，不是重新创作剧情。

| 上游 | 写进提示词 |
|------|------------|
| Director | 景别、主体、戏剧 beat、情绪 |
| Look | 可见光色结果（不写岗位黑话） |
| Cinematography | 焦段、角度、运镜 |
| Dialogue + **linked_dialogue** | **只写本镜绑定台词**；说话人要可辨认 |
| Timing / packages | 本段时长 + 时间轴 beats |
| Style pack | 类型气质 |

每段生成任务产出 **两版 × 双语**（均可直接投喂）：

| 字段 | 用途 |
|------|------|
| `actor_free_prompt` / `_zh` | 演员自由发挥版 |
| `director_guided_prompt` / `_zh` | 导演指导版（更具体） |
| `visual_prompt` / `motion_prompt` | 技术层 |
| `zh_director_summary` | 镜头一句话摘要 |

**四段固定结构：**

1. 指定主体 / SUBJECT（`图1是××`）  
2. 摄影设备与参数  
3. 故事线（时间轴分镜 + 表演/台词/光影；**不写**「自行切镜更流畅」等流程话）  
4. 音效（有源 SFX；无配乐、无字幕、无水印）

### 交付目录

每次跑完写入：

```text
outputs/<project_id>/
  README.txt
  prompt_board.html        # 浏览器打开：一键「复制」+ 自动换行
  prompt_board.md          # 全片提示词板 + 文末「电影最终时长统计」（自动换行）
  clips/                   # 每段纯文本（自动换行，可直接投喂）
    G01_director_guided.zh.txt
    G01_director_guided.en.txt
    ...
  assets/                  # 有资产轨时
    asset_board.md
    asset_bible.json
    characters/ props/ sets/
```

内部状态仍在 `film_pipeline/bible/projects/<project_id>/`（默认 gitignore）。

```bash
film-pipeline timing --project demo
film-pipeline prompts --project demo
film-pipeline prompts --project demo --shot S01_T05
```

## 仓库结构

```text
ai-film-pipeline/
├── AGENTS.md               # 外来智能体强制规范
├── agents/                 # 方案 B 包装注册表
├── skills/                 # 岗位 Skill（SKILL.md + schema）
│   └── prompt_writer/      # 最终提示词写手
├── knowledge/
│   ├── human/              # 人维护版（Markdown）
│   ├── ai/                 # AI 运行版（JSON）
│   ├── camera/ · timing/ · style_packs/
│   └── README.md
├── schemas/
├── film_pipeline/
│   ├── cli.py
│   ├── orchestrator/
│   └── runtime/            # timing 打包、prompt_writer、critic…
├── tests/
├── scripts/
└── outputs/                # 交付件（gitignore）
```

### 知识库双版本

| 版本 | 路径 | 用途 |
|------|------|------|
| 人读 | `knowledge/human/` | 理念、案例、禁忌、协作 |
| AI | `knowledge/ai/` | 枚举、映射、交接合同、质检 |

```bash
python scripts/validate_knowledge_dual.py
```

## 快速开始

### 1. 安装

```bash
cd ai-film-pipeline
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate

pip install -e ".[dev]"
copy .env.example .env   # Windows
# cp .env.example .env
```

默认 `FILM_PIPELINE_DRY_RUN=1`：**不调用在线 LLM**，用规则 + 模板跑通全流程。

### 2. 跑通示例

```bash
# 交互
python -m film_pipeline.cli run --script film_pipeline/bible/examples/sample_script.txt --project demo

# 非交互
python -m film_pipeline.cli run --script film_pipeline/bible/examples/sample_script.txt --project demo --max-clip 30 --style neo_noir --assets
```

| 位置 | 内容 |
|------|------|
| `outputs/demo/` | **用户拿的交付**（提示词板 + clips + assets） |
| `film_pipeline/bible/projects/demo/` | 内部 FilmBible / brief / task_log |

```bash
film-pipeline tasks --project demo
film-pipeline brief --project demo
film-pipeline assets --project demo
film-pipeline prompts --project demo
```

### 3. 只跑某一阶段

```bash
film-pipeline step --project demo --stage look
film-pipeline step --project demo --stage cinematography
```

### 4. 接入真实 LLM

```env
FILM_PIPELINE_DRY_RUN=0
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

兼容任何 OpenAI 协议端点。Live 失败**默认不静默回退 stub**（除非显式 `FILM_PIPELINE_STUB_FALLBACK=1`）。

## Skill 与知识库

| Agent | Skill | 主要知识库 |
|-------|-------|------------|
| Dramaturg | `skills/dramaturg` | `knowledge/storycraft` |
| Dialogue | `skills/dialogue` | `knowledge/dialogue` |
| Director | `skills/director` | `knowledge/directing` |
| Look | `skills/look` | `knowledge/look`, `style_packs` |
| Cinematography | `skills/cinematography` | `knowledge/camera`, `look` |
| Timing | `skills/timing` | `knowledge/timing` |
| **Prompt Writer**（阶段 generator） | `skills/prompt_writer` | 合同 → 可投喂正文 |
| Critic | `skills/critic` | 结构 / 对白 / 说话人 / 绑定 |
| Asset（旁路） | `skills/asset` | 三视图 sheet |

扩展：改 `skills/<name>/`、改 `knowledge/**`、加 `style_packs` / `exemplars`。

### 导入运镜 Excel

```bash
python scripts/import_camera_xlsx.py --xlsx "path/to/catalog.xlsx"
```

## FilmBible 核心字段

- `story` / `characters` / `scenes` — 剧作  
- `dialogue` — 定稿对白  
- `shots[]` — 镜头合同（含 `linked_dialogue`）  
- `look_bible` — 影调  
- `generation_packages` / `generation_jobs` — 生成段与最终提示词  
- `timing_plan` — 时长账本（含 `film_total_sec`）  
- `asset_bible` — 资产设定  

## 设计原则

1. **合同优于闲聊**：Schema + 字段白名单  
2. **规则表优先于玄学 prompt**：情绪 → 影调 / 运镜候选  
3. **精确重拍**：Critic 指定 `reroute_to`  
4. **投喂正文只写画面**：流程说明写在 Skill / board 脚注，不写进模型提示词  
5. **人在环**：关键对白与分镜可人工确认（后续 `approve` gate）

## 开发

```bash
pytest
ruff check film_pipeline
```

## 路线图

- [x] Skill + 知识库骨架  
- [x] 状态机编排 + dry-run / live 显式模式  
- [x] Look 独立节点 + 资产旁路  
- [x] Prompt Writer 双语文成品 + 自动换行  
- [x] Timing 打包 `generation_packages`（15/30 cap + 时间轴分镜）  
- [x] Critic：对白覆盖 / 说话人 / 镜句绑定  
- [x] 交付 `outputs/<project>/` + 电影最终时长统计  
- [x] 外来 Agent 方案 A/B（`AGENTS.md`）  
- [ ] 人审 gate 真正暂停等待确认  
- [ ] 向量检索 exemplars  
- [ ] Web 导演台（可选）

## License

MIT
