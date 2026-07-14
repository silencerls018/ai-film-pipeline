# 06 · 时长规划（Timing）· 人维护

> **AI 同步：** `ai/timing/rules.json` · 参数表 `knowledge/timing/*.json`

## 职责
根据**台词朗读 + 停顿 + 运镜最小时间 + 留白**估算每镜时长；按用户选定的 **15s 或 30s 单段上限** 打包生成段。

## 核心公式
```text
有台词: needed ≈ pre + max(dialogue_sec, move_sec) + post
无台词: needed ≈ pre + move_sec + post
连续镜头 → generation_packages[]（每包 duration ≤ max_clip）
单镜本身 > max_clip → 拆 generation_clips[] 再各成包（段间可 overlap）
```

## 专业要点
1. **15/30 是单次生成 cap，不是整片时长。**  
2. **段内**用时间轴分镜（`0-2秒，…`）；**只有累计到底塞不下**才开下一段。  
3. 中文语速约 2.5–4 字/秒（戏剧可更慢）。  
4. 慢推等运镜有最小可读时间，不能压成 0.5s。  
5. 写入 `timing_plan.film_total_sec` / `generation_total_sec`，交付板文末统计电影最终时长。

## 与写手
每个 **package** = 一条最终提示词任务；段内 beats 带相对时间轴；`duration_sec` 必须写入提示词故事线。  
