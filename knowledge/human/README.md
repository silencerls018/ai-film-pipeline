# 人维护版知识库

面向你自己 / 合作主创。写清楚**为什么、何时用、禁忌、与上下游怎么交**。

## 怎么改

1. 先改本目录对应 `0x_*.md`  
2. 同步修改 `knowledge/ai/**` 里的 JSON 枚举与规则  
3. 运行：`python scripts/validate_knowledge_dual.py`  
4. 再 `film-pipeline run` 验证  

## 文档列表

| 文件 | 岗位 |
|------|------|
| `00_shared_emotions_and_handoffs.md` | 全员共享词表与交接 |
| `01_dramaturg.md` | 剧作 |
| `02_dialogue.md` | 对白 |
| `03_director.md` | 导演分镜 |
| `04_look.md` | 影调 |
| `05_cinematography.md` | 摄影（含 Excel 运镜库说明） |
| `06_timing.md` | 时长 |
| `07_asset.md` | 资产三视图 |
| `08_generator.md` | 最终提示词编译 |
| `09_critic.md` | 质检 |
| `10_orchestrator.md` | 调度总指挥 |

总说明见上级 `knowledge/README.md`。
