# 03 · 导演分镜（Director）· 人维护

> **AI 同步：**  
> `ai/director/shot_syntax.json`  
> `ai/director/coverage_patterns.json`  
> `ai/director/performance_physics.json`（参考 `E:\AI\skill\情绪导演_Skill_V2.2.md`）  
> `ai/director/shot_performance_lighting.json`  
> `ai/director/dual_prompt_policy.json`  
> `ai/look/lighting_for_emotion.json`

## 职责（扩大后）

导演不只「切镜头」，而是设计：

```text
戏（beat）
  + 表演（情绪如何长在脸上/身上）
  + 景别与覆盖
  + 运镜倾向
  + 灯光氛围
```

并保证它们 **同一情绪下不打架**。

## 最终提示词双版本（编译器出）

| 版本 | 字段 | 内容 |
|------|------|------|
| **演员自由发挥版** | `actor_free_prompt` | 只给情绪词 + 强度 + 戏剧目的 + 景别/时长框，**不写死肌肉表演** |
| **导演指导版** | `director_guided_prompt` | 生理表情/微动作/视线 + 景别 + 运镜(含精品库英文) + 灯光 + 台词 delivery |

两版共享：同一 `shot_id`、同一时长 cap、同一故事 beat。

## 专业要点

1. **禁止文学修辞**（心如刀割→双手按胸、呼吸急促、面部肌肉扭曲）。  
2. **情绪 → 可拍摄生理**（见 performance_physics）。  
3. **微动作必有**，避免 AI 木偶脸。  
4. **灯光服务情绪与情节**（压迫：冷阴影高反差；亲密：暖实用光柔比；揭示：抬局部反差护眼）。  
5. **运镜服务表演**：揭示用推近/揭示运镜；亲密少环绕；压迫慢推+收景别。  
6. **景别节奏**：建立→关系→细节→反应。  

## 与下游

| 下游 | 拿什么 |
|------|--------|
| 影调 | 情绪弧 + 场基调 |
| 摄影 | 景别/beat + 运镜倾向 + 灯光计划 |
| 时长 | 分镜与台词 |
| Generator | 组装双版提示词 |

## 参考来源（工程化摘要）

- 你的《情绪导演 Skill》：物理优先、禁修辞、情绪生理表、微动作层次、光影相对描述  
- 电影实践：coverage、动机光、情绪光比、正反打与反应镜  
- 本项目：共享 7 情绪键 + 15/30 拆 clip + 运镜精品库  

非学术引用集，是可执行手册。
