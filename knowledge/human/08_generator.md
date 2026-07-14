# 08 · 提示词编译（Generator）· 人维护

> **AI 同步：** `ai/generator/compile_rules.json`

## 职责
**组装**最终提示词，不重新创作剧情。本管线终点。

## 必须合并的上游
导演 beat/景别 · 摄影运镜(含精品库 prompt_en) · 影调 · 对白表演提示 · 时长 · 可选 asset_id

## 输出字段
- `visual_prompt` / `motion_prompt` / `master_prompt` / `negative_prompt`  
- `duration_sec` ≤ 15 或 30  
- `zh_director_summary` 给人看  

## 铁律
**Spec 没有的情节、人物、道具，禁止写入。**  
