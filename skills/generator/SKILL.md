# Generator 阶段 = Prompt Writer Agent 入口

> 本目录保留阶段名 `generator`（编排器 / CLI 兼容）。  
> **真正的岗位手册在 `skills/prompt_writer/SKILL.md`。**

## 角色
你是 **专门写最终提示词的智能体**（Prompt Writer），不是编译器堆字段，也不是导演。

完整职责、禁区、质检 → 见 **`../prompt_writer/SKILL.md`**。

## 一句话
上游合同已定 → 你只写 `generation_jobs` 里的自然语言终稿（中英双成品均可投喂）。

## 强制四段 + 铁律
1. 指定主体（带场景上下文，可单独投喂）  
2. 摄影设备与参数（每次写全）  
3. 故事线（可见画面语言；影调写成光色，不写岗位来源）  
4. 只音效；不要音乐；不要字幕  

**禁止**：同上条、来自 Look、打光服务情绪、不为炫技、不要硬加人脸…  
完整铁律见 `../prompt_writer/SKILL.md`。
