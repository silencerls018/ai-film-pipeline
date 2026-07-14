# 06 · 时长规划（Timing）· 人维护

> **AI 同步：** `ai/timing/rules.json` · 参数表 `knowledge/timing/*.json`

## 职责
根据**台词朗读 + 停顿 + 运镜最小时间 + 留白**估算每镜时长；按用户选定的 **15s 或 30s** 拆 clip。

## 核心公式
```text
有台词: needed ≈ pre + max(dialogue_sec, move_sec) + post
无台词: needed ≈ pre + move_sec + post
若 needed > max_clip → 拆 generation_clips[]（段间可 overlap）
```

## 专业要点
1. **模型 cap 是单段，不是整片**。  
2. 中文语速约 2.5–4 字/秒（戏剧可更慢）。  
3. 慢推等运镜有最小可读时间，不能压成 0.5s。  
4. 宁可导演多拆正反打，也不要单镜硬撑 40s 不拆。  

## 与编译
每个 clip = 一条最终提示词任务；`duration_sec` 必须写入 prompt。  
