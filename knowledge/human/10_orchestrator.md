# 10 · 调度总指挥（Orchestrator）· 人维护

> **AI 同步：** `ai/orchestrator/policy.json`

## 职责
读 ProductionBrief，发 TaskTicket，跑主链与资产旁路。  
**不写艺术内容**，只调度与校验合同边界。

## 开机顺序
1. 用户选 15/30、风格、是否资产  
2. 写 Brief  
3. 主链：剧作→…→提示词→质检  
4. 剧作完成后可 fork 资产轨  

## 派工原则
- 每岗只给切片输入  
- 只允许写合同字段  
- 失败精确重跑  

人是创作总指挥；Orchestrator 是调度总指挥。  
