# 独立智能体包装（Agent Packages）

本目录描述 **如何把本仓库拆成互不污染的岗位智能体**。

## 权威文件

| 文件 | 用途 |
|------|------|
| [`../AGENTS.md`](../AGENTS.md) | **任何外来智能体必读**：先问用户 A/B 方案 |
| [`registry.json`](./registry.json) | 每岗 Skill / 知识库 / 读写字段白名单 |

## 两个方案（由用户选，不是项目替用户选）

1. **A 单智能体全包** — 一个执行者按顺序完成；仍按岗写字段  
2. **B 多智能体分工** — 每岗一个 Agent，**只安装自己的 skill + 知识库**

## 独立性保证（方案 B）

对每个 `packages[]` 条目：

```text
安装/加载 = skill + schema + knowledge_paths
输入     = FilmBible[reads] 切片
输出     = 仅 writes 字段的 JSON
禁止     = 其它 skill、其它 knowledge、改 forbidden 字段、岗间闲聊
```

调度者只做：派工 → 校验 schema → merge → 存 `film_bible.json`。

## 与 Python CLI 的关系

- CLI / dry-run：**可选本地工具**，方便骨架跑通  
- **不要求**配置 API 才能理解架构  
- 真正的「多智能体」由 **外部 Agent 运行时** 按 `AGENTS.md` 拉起  

阶段名别名：`prompt_writer` ↔ CLI `generator`（见 registry `cli_stage_alias`）。
