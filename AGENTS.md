# 给「来运行本项目」的智能体（必读）

本文件约束 **任何外部智能体**（Claude / Cursor / Grok / 人工编排的 Agent 等）如何操作本仓库。

## 0. 本项目不管什么

| 不管 | 说明 |
|------|------|
| **视频模型 API** | 终点是提示词文件，不调用可灵/即梦/Runway 等 |
| **写提示词用的大模型账号** | 不由本仓库统一托管；谁运行谁自带能力 |
| **替用户选方案** | 开工前必须先问用户（见下） |

Python CLI 里的 `OPENAI_*` / dry-run **只是本地可选工具**，不是「多智能体架构」本身。  
**架构真相是：Skill + 知识库 + FilmBible 合同。**

---

## 1. 开工第一问（强制）

在读剧本、改文件、开跑流水线之前，**必须先问用户**，二选一：

### 方案 A — 单智能体全包

> 由 **你自己** 按岗位顺序完成全部工作（可顺序读取多个 Skill，但仍是同一个执行者）。

- 适合：短剧本、快速试跑、用户只要结果  
- 你仍须 **按阶段隔离写入字段**（不能一次改完所有 FilmBible 字段乱写）  
- 顺序见下文「主链顺序」

### 方案 B — 多智能体分工（每岗独立）

> 拆成 **多个独立智能体**，**每个智能体只做一件事**。  
> **每个智能体只安装 / 只加载自己的 Skill + 自己的知识库**，互不共享手册。

- 适合：要可控、可追责、要保证岗位边界  
- **禁止**给某个岗位智能体塞其它岗位的 `SKILL.md` 或知识目录  
- **禁止**岗位之间自由聊天；只通过 **FilmBible JSON** 交接  
- 调度者（可以是你或代码 Orchestrator）只负责：派工、合并字段、存盘、问用户 Brief

**未得到用户明确选择前，不得擅自开跑。**

用户若说「你看着办」：默认 **方案 A**，并在回复里写明「已按方案 A 执行」。

---

## 2. 方案 B：独立智能体包装清单

权威注册表：[`agents/registry.json`](agents/registry.json)

每个包装 = **可独立交付的 Agent 包**：

```text
仅允许加载：
  - skills/<id>/SKILL.md
  - skills/<id>/schema.json
  - knowledge 列表中的路径（见 registry）
  - FilmBible 中「只读字段」切片
  - 本包装的 writes 白名单

禁止加载：
  - 其它 skills/*
  - 其它岗位 knowledge/*
  - 完整未切片的「让我随便改」权限
```

### 主链顺序（方案 A/B 相同）

```text
1. producer（人）→ ProductionBrief
2. dramaturg
3. dialogue          （可 skip polish → passthrough）
4. director
5. look
6. cinematography
7. timing            （可用代码确定性；仍算独立岗位）
8. prompt_writer     （阶段名 generator；专门写最终提示词）
9. critic
```

可选旁路（可与主链解耦）：

```text
asset（建议在 dramaturg 之后；不堵主链）
```

### 交接规则（保证独立）

1. **合同优于闲聊**：只写 schema / registry 允许的字段  
2. **非法字段剥离**：下游不得依赖上游随口加的私货字段  
3. **中英双成品均可投喂**：`prompt_writer` 写 `generation_jobs`；其它岗不抢写  

4. **Seedance / 外部 Skill**：仅外部参考，**不是**本仓库主功能，不得替换 FilmBible 合同  

---

## 3. 方案 A 怎么干

1. 问清 Brief：`max_clip` 15|30、风格、是否资产轨、是否对白精修  
2. 建项目：`film_pipeline/bible/projects/<id>/film_bible.json`  
3. **按顺序**扮演各岗：每岗只读该岗 Skill+知识，写完再进入下一岗  
4. 每岗结束存盘；最后导出 `prompt_board.md`  
5. 可用 CLI：`film-pipeline run ...` 作 dry-run 骨架，但内容责任仍在你  

即：一个身体，多套工牌；**工牌不能同时戴乱**。

---

## 4. 方案 B 怎么干

1. 同样先问 Brief  
2. 调度者按 `agents/registry.json` **依次或并行（仅 asset）拉起子智能体**  
3. 每个子智能体启动时 **只注入**：

```text
- 你的角色名与唯一任务
- skills/<id>/SKILL.md + schema.json
- registry 中 knowledge_paths 的文件
- film_bible 只读切片（reads）
- 要求：只输出 writes 对应 JSON，禁止改其它字段
```

4. 调度者校验 schema → merge 进 FilmBible → 再派下一岗  
5. **子智能体之间禁止互相 @、禁止共享完整对话历史**（只共享 FilmBible）

并行仅允许：`asset` 与主链在 dramaturg 之后的安全窗口；合并时字段不打架（asset 只写 `asset_bible`）。

---

## 5. ProductionBrief（两种方案都要）

跑之前向用户确认（或 CLI 参数一次给齐）：

| 项 | 选项 |
|----|------|
| max_clip_sec | 15 或 30 |
| style_pack | 如 neo_noir / warm_realism |
| run_asset_track | 是 / 否 |
| run_dialogue_polish | 是 / 否（否=保留原剧本台词） |
| project_id | 项目名 |
| script | 剧本路径或正文 |

---

## 6. 产出物

```text
outputs/<project_id>/                 # 用户交付（出厂件）
  prompt_board.md                     # 中英均可投喂 + 文末电影最终时长
  clips/*.txt
  assets/                             # 可选

film_pipeline/bible/projects/<project_id>/   # 内部状态
  production_brief.json
  film_bible.json                     # 唯一真相
  timing_plan.md                      # 可选
```

**本仓库不负责**：把提示词打进即梦/可灵账号。

---

## 7. 给调度者的检查清单

- [ ] 已问用户：方案 A 还是方案 B  
- [ ] 已收齐 Brief  
- [ ] 方案 B 下每个子 Agent 只挂载自己的 Skill+知识库  
- [ ] 无跨岗改字段  
- [ ] `prompt_writer` 只写 `generation_jobs`，不回头改 shots  
- [ ] 未把外部 Seedance Skill 当成主架构  

---

## 8. 快速命令（可选工具，不是架构）

```bash
cd ai-film-pipeline
pip install -e ".[dev]"
# dry-run 骨架（不调用在线模型）
film-pipeline run --script <剧本> --project <名> --max-clip 30 --style neo_noir --no-dialogue
film-pipeline org
film-pipeline stages
```

多智能体「真分工」时：以本文件 + `agents/registry.json` 为准拉起子 Agent，**不要**假设必须配置本仓库的 API Key。
