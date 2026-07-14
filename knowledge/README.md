# 知识库双版本说明（人 × AI）

本目录采用 **双版本协作**：

| 版本 | 路径 | 读者 | 形态 |
|------|------|------|------|
| **人维护版** | `knowledge/human/` | 编剧、导演、你自己 | Markdown，可读、可改、可评论 |
| **AI 运行版** | `knowledge/ai/` | Orchestrator / 各岗位 Agent | JSON，字段稳定、可校验 |

另有：

| 路径 | 说明 |
|------|------|
| `knowledge/camera/` | 运镜 Excel 导入的大词库（AI 用，人用 Excel 维护源） |
| `knowledge/style_packs/` | 风格包（AI 用） |
| `knowledge/timing/` | 时长参数（AI 用） |

## 协作原则（必读）

1. **共享词表优先**  
   所有岗位只使用 `ai/shared/emotion_keys.json` 里的情绪键，以及 `handoff_contracts.json` 里的交接字段。  
   人改概念时，先改 `human/00_shared_*.md`，再同步改 `ai/shared/*.json`。

2. **人改散文，机改表格**  
   - 原理、案例、禁忌说明 → 写在 `human/`  
   - 枚举、映射、阈值、候选列表 → 写在 `ai/`

3. **不同步就禁止上线**  
   改完人读版后，必须更新对应 AI JSON（或跑校验脚本）。  
   校验：`python scripts/validate_knowledge_dual.py`

4. **交接靠合同，不靠聊天**  
   上一岗只写自己 `writes` 字段；下一岗只读 `reads`。见 `ai/shared/handoff_contracts.json`。

5. **运镜大词库例外**  
   158 条精品运镜：人用 Excel 维护 → `scripts/import_camera_xlsx.py` → `knowledge/camera/`。  
   人读说明见 `human/05_cinematography.md`。

## 岗位对照

| 岗位 | 人读 | AI |
|------|------|-----|
| 共享 | `human/00_*.md` | `ai/shared/` |
| 剧作 | `human/01_dramaturg.md` | `ai/dramaturg/` |
| 对白 | `human/02_dialogue.md` | `ai/dialogue/` |
| 导演 | `human/03_director.md` | `ai/director/` |
| 影调 | `human/04_look.md` | `ai/look/` |
| 摄影 | `human/05_cinematography.md` | `ai/camera/` + `camera/` 词库 |
| 时长 | `human/06_timing.md` | `ai/timing/` + `timing/` |
| 资产 | `human/07_asset.md` | `ai/asset/` |
| 提示词编译 | `human/08_generator.md` | `ai/generator/` |
| 质检 | `human/09_critic.md` | `ai/critic/` |
| 总指挥 | `human/10_orchestrator.md` | `ai/orchestrator/` |

## 专业依据（摘要）

人读文档综合了常见电影工业实践与叙事理论（分场功能、潜台词、正反打覆盖、景别句法、光比影调、轴线等），并结合本仓库「剧本→镜头合同→最终提示词」的 AI 电影流程做了工程化裁剪。  
**不是学术论文引用集**，而是可执行的岗位手册 + 机器表。
