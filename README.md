# AI Film Pipeline

多智能体「虚拟剧组」管线：把剧本推进为结构化 **FilmBible**，终点是 **最终提示词**（不调用视频 API）。

> **ProductionBrief = 创作意图** · **Orchestrator = 调度总指挥** · **TaskTicket = 派工单**  
> **Skill = 岗位手册** · **Knowledge = 规则库** · **FilmBible = 本片状态**

## 架构（更合理）

```text
你 / Producer
  → ProductionBrief（必选：15|30 秒、风格包、是否资产轨）
       ↓
Orchestrator（代码总指挥 · 唯一派工者）
  ├─ 主链 main
  │    dramaturg → dialogue → director → look
  │    → cinematography → timing → generator → critic
  └─ 资产旁路 assets（可选并行）
       asset：人物/道具/场景三视图提示词
       image_refs 可空，随时换图，不堵主链
```

```bash
film-pipeline org          # 组织架构
film-pipeline stages       # 岗位列表
```

### 开始前：必须选择 15 秒或 30 秒

视频模型只有两种单段上限，**跑流水线之前先问用户**：

| 选项 | 含义 |
|------|------|
| **15 秒** | 短时长视频模型 |
| **30 秒** | 长时长视频模型 |

```bash
# 交互询问（推荐）
film-pipeline run --script ... --project demo

# 或启动时直接指定（脚本/CI 用）
film-pipeline run --script ... --project demo --max-clip 15
film-pipeline run --script ... --project demo --max-clip 30
```

**本仓库终点是最终提示词**（`prompt_board.md` / `generation_jobs`），不调用视频 API。

时长规划按所选上限拆 clip：

```text
needed ≈ pre_roll + max(dialogue_sec, move_sec) + post_hold
若 needed > max_clip → 拆 generation_clips[]（每段 ≤ 15 或 30）
```

```bash
film-pipeline timing --project demo
film-pipeline prompts --project demo
```

### 最终提示词从哪来？

`generator` 阶段是 **Prompt Compiler**（不是重新拍脑袋写 prompt）：

| 上游 | 并入提示词的内容 |
|------|------------------|
| Director | 景别、主体、戏剧 beat、情绪 |
| Look | 全片/场次影调、色板、禁用项 |
| Cinematography | 焦段、角度、运镜+动机、灯光 |
| Dialogue | 台词表演提示（delivery/subtext） |
| Style pack | 类型气质 |

每镜产出 **两版 × 双语**：

| 字段 | 语言 | 用途 |
|------|------|------|
| **`actor_free_prompt`** | **英文主稿** | 自由发挥版，复制去视频模型 |
| **`director_guided_prompt`** | **英文主稿** | 导演指导版，复制去视频模型 |
| `actor_free_prompt_zh` / `director_guided_prompt_zh` | 中文辅助 | **只帮你看懂**，不优先投喂 |
| `visual_prompt` / `motion_prompt` | 技术层 | 关键帧 / I2V |
| `zh_director_summary` | 中文 | 镜头一句话摘要 |

`prompt_board.md` 里每版都是：**英文主稿在上，中文对照在下**。

```bash
film-pipeline prompts --project demo
film-pipeline prompts --project demo --shot S01_T05
```

编排器按状态机调用各岗；Agent **不自由群聊**，只读写 FilmBible 中自己的字段。

## 仓库结构

```text
ai-film-pipeline/
├── skills/                 # 岗位 Skill（SKILL.md + schema）
├── knowledge/
│   ├── human/              # 人维护版（Markdown 手册）
│   ├── ai/                 # AI 运行版（JSON 规则/词表/交接合同）
│   ├── camera/             # 运镜 Excel 导入大词库
│   ├── timing/ · style_packs/
│   └── README.md           # 双版本协作说明
├── schemas/
├── film_pipeline/
├── tests/
└── scripts/
    ├── import_camera_xlsx.py
    └── validate_knowledge_dual.py
```

### 知识库双版本

| 版本 | 路径 | 用途 |
|------|------|------|
| 人读 | `knowledge/human/` | 理念、案例、禁忌、上下游协作 |
| AI | `knowledge/ai/` | 枚举、映射、交接合同、质检量表 |

改完后校验：

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

默认 `FILM_PIPELINE_DRY_RUN=1`：**不调用在线 LLM**，用规则 + 模板跑通全流程，方便本地体验。

### 2. 跑通示例（先填 Brief，再由 Orchestrator 派工）

交互（推荐）——依次问：15/30、风格、是否资产轨：

```bash
python -m film_pipeline.cli run --script film_pipeline/bible/examples/sample_script.txt --project demo
```

非交互一次给齐：

```bash
python -m film_pipeline.cli run --script film_pipeline/bible/examples/sample_script.txt --project demo --max-clip 30 --style neo_noir --assets
```

产出目录 `film_pipeline/bible/projects/demo/`：

| 文件 | 含义 |
|------|------|
| `production_brief.json` | 开工意图 |
| `film_bible.json` | 全状态 + task_log |
| `prompt_board.md` | **主链终点：镜头提示词** |
| `asset_board.md` | 三视图设定提示词（可换图） |
| `timing_plan.md` | 时长账本 |

```bash
film-pipeline tasks --project demo    # 派工日志
film-pipeline brief --project demo
film-pipeline assets --project demo   # 仅重跑资产旁路
film-pipeline prompts --project demo  # 最终提示词
```

### 3. 只跑某一阶段

```bash
film-pipeline step --project demo --stage look
film-pipeline step --project demo --stage cinematography
```

### 4. 接入真实 LLM

在 `.env` 中设置：

```env
FILM_PIPELINE_DRY_RUN=0
OPENAI_API_KEY=sk-...
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-4o-mini
```

兼容任何 OpenAI 协议端点（含代理 / 本地网关）。

## Skill 与知识库

| Agent | Skill 路径 | 主要知识库 |
|-------|------------|------------|
| Dramaturg | `skills/dramaturg` | `knowledge/storycraft` |
| Dialogue | `skills/dialogue` | `knowledge/dialogue` |
| Director | `skills/director` | `knowledge/directing` |
| Look | `skills/look` | `knowledge/look`, `style_packs` |
| Cinematography | `skills/cinematography` | `knowledge/camera`, `look`, `style_packs` |
| Timing | `skills/timing` | `knowledge/timing`（语速、运镜时长、15/30 cap） |
| Generator | `skills/generator` | 编译最终镜头提示词 |
| Critic | `skills/critic` | 评分与失败分类 |
| **Asset（旁路）** | `skills/asset` | 人物/道具/场景三视图 prompt |

扩展方式：

1. 改 `skills/<name>/SKILL.md`（职责与步骤）
2. 改 `knowledge/**/*.json`（规则与候选集）
3. 加 `knowledge/style_packs/*.json`（风格包）
4. 加 `knowledge/exemplars/*.json`（好样本镜头合同）

### 导入运镜 Excel 知识库

维护源可以是你的 xlsx（如 `E:\AI\知识库\提示词\运镜Prompt精品库_清洗版.xlsx`），**运行时只读 JSON**：

```bash
python scripts/import_camera_xlsx.py
# 或
python scripts/import_camera_xlsx.py --xlsx "E:\AI\知识库\提示词\运镜Prompt精品库_清洗版.xlsx"
```

生成：

- `knowledge/camera/moves_catalog.json` — 全量运镜词条 + 英文 Prompt
- `knowledge/camera/shot_sizes.json` — 景别
- `knowledge/camera/emotion_to_camera.json` — 情绪 → 候选运镜（供摄影岗）
- `knowledge/camera/CATALOG_README.md` — 导入摘要

Excel 继续当你的编辑台；大改后重新跑导入即可。

## FilmBible 核心字段

- `story` / `characters` / `scenes` — 剧作层
- `dialogue` — 定稿对白
- `shots[]` — 镜头合同（戏剧 + camera + look）
- `look_bible` — 全片与分场影调
- `assets` / `reviews` — 生成物与质检

单镜同时包含 **运镜** 与 **影调**，且都应有 `motivation`。

## 设计原则

1. **合同优于闲聊**：强制 JSON Schema，非法字段剥离  
2. **规则表优先于玄学 prompt**：情绪 → 影调 / 运镜候选  
3. **精确重拍**：Critic 指定 `reroute_to`，不整片重来  
4. **人在环**：对白、关键分镜、关键帧建议人工确认（CLI 后续可加 `approve`）

## 开发

```bash
pytest
ruff check film_pipeline
```

## 路线图

- [x] Skill + 知识库骨架
- [x] 状态机编排 + dry-run
- [x] Look（影调）独立节点
- [x] Prompt Compiler（合并全部成果为最终提示词 + prompt_board.md）
- [x] Timing Planner（台词/运镜时长 + 15/30s cap 拆 clip）
- [x] 开始前强制选择视频上限 15s 或 30s（提示词为终点，不接 API）
- [x] ProductionBrief + Orchestrator 派工（TaskTicket）+ 资产旁路
- [ ] 人审 gate 真正暂停等待确认
- [ ] 向量检索 exemplars
- [ ] Web 导演台（可选 TypeScript 前端）

## License

MIT
