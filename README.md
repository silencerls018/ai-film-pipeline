# AI Film Pipeline

多智能体「虚拟剧组」管线：把剧本推进为结构化 **FilmBible（电影圣经）**——含优化对白、分镜、**影调 Look**、摄影机语言（焦段 / 角度 / 运镜 / 动机），并为后续 AI 出图出片预留生成与质检节点。

> **Skill = 岗位怎么干** · **Knowledge = 电影语法与规则** · **FilmBible = 本片状态**

## 架构

```text
剧本
  → Dramaturg     结构 / 人物 / 场次 / 情绪曲线
  → Dialogue      对白深度（潜台词、功能、节奏）
  → Director      分镜叙事（景别、beat、剪辑意图）
  → Look          全片 & 分场影调 / 色彩剧本
  → Cinematography  单镜：角度·焦段·运镜·光色落地
  → Generator     **Prompt 编译器**：合并全部成果 → 最终提示词
  → Critic        对照合同质检，精确打回
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

每镜产出：

- `visual_prompt` — 关键帧 / 文生图  
- `motion_prompt` — 图生视频运镜  
- `master_prompt` — 视觉+运动合一  
- `negative_prompt` — 负向词  
- `zh_director_summary` — 中文镜头摘要  

并导出可读文件：`film_pipeline/bible/projects/<id>/prompt_board.md`

```bash
film-pipeline prompts --project demo
film-pipeline prompts --project demo --shot S01_T05
```

编排器按状态机调用各岗；Agent **不自由群聊**，只读写 FilmBible 中自己的字段。

## 仓库结构

```text
ai-film-pipeline/
├── skills/                 # 岗位 Skill（SKILL.md + schema）
├── knowledge/              # 知识库（影调、运镜、风格包…）
├── schemas/                # 共享 JSON Schema
├── film_pipeline/
│   ├── cli.py              # 命令行入口
│   ├── runtime/            # 加载 skill / 检索 kb / 调 LLM / 校验
│   ├── orchestrator/       # 状态机流水线
│   └── bible/              # 示例与项目实例
├── tests/
└── scripts/
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

### 2. 跑通示例剧本

```bash
film-pipeline run --script film_pipeline/bible/examples/sample_script.txt --project demo
```

或：

```bash
python -m film_pipeline.cli run --script film_pipeline/bible/examples/sample_script.txt --project demo
```

输出目录：`film_pipeline/bible/projects/demo/film_bible.json`

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
| Generator | `skills/generator` | 模型能力 / prompt 模板 |
| Critic | `skills/critic` | 评分与失败分类 |

扩展方式：

1. 改 `skills/<name>/SKILL.md`（职责与步骤）
2. 改 `knowledge/**/*.json`（规则与候选集）
3. 加 `knowledge/style_packs/*.json`（风格包）
4. 加 `knowledge/exemplars/*.json`（好样本镜头合同）

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
- [ ] 人审交互（approve / edit shot）
- [ ] 关键帧 / 视频 API 适配器
- [ ] 向量检索 exemplars
- [ ] Web 导演台（可选 TypeScript 前端）

## License

MIT
