# 09 · 质检（Critic）· 人维护

> **AI 同步：** `ai/critic/rubric.json`

## 职责
对照 FilmBible 合同找问题，输出 `reroute_to`，**不直接改艺术字段**。

## 检查维度
1. 情绪键是否合法  
2. 运镜/影调是否有 motivation  
3. 是否违反 look forbidden  
4. clip 是否超 max_clip  
5. 提示词是否覆盖镜头  
6. 资产是否缺主角色（若开了资产轨）

## 打回原则
精确打回，不整片重来。运镜错 → cinematography；超时 → timing；台词功能空 → dialogue。  
