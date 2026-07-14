# AI 运行版知识库

面向 Orchestrator 与各岗位 Agent。字段稳定、可 JSON Schema 化、可校验。

## 加载约定

`KnowledgeStore.retrieve_for_stage(stage)` 会优先读取本目录，并合并：

- `shared/` 全员词表与交接合同  
- 岗位子目录规则  
- 大词库仍在 `knowledge/camera/`、`knowledge/timing/`、`knowledge/style_packs/`（体积大、Excel/参数表）

## 禁止

- 在 AI JSON 里写成长篇散文（放到 `human/`）  
- 私自新增 emotion key 却不改 `shared/emotion_keys.json`  
- 让 Agent 读取 `human/` 全文当唯一知识源（可引用摘要，但以 JSON 为准）
