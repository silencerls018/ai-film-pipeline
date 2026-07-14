# 00 · 共享情绪词表与岗位交接（人维护）

> **同步文件：** `ai/shared/emotion_keys.json` · `ai/shared/handoff_contracts.json` · `ai/shared/vocabulary.json`  
> 改这里之后，请立刻改 AI JSON，否则 Agent 会各说各话。

---

## 1. 为什么必须共享

多智能体协作失败的头号原因是：  
剧作写「压抑」，摄影写 `oppression`，影调写「low mood」——**同一情绪三种叫法**。

约定：**对内一律用 emotion key（英文蛇形）**；对人展示可用中文标签。

---

## 2. 标准情绪键（全管线唯一）

| key | 中文 | 何时用 | 典型视听倾向（给摄影/影调） |
|-----|------|--------|------------------------------|
| `calm` | 平静/建立 | 日常、环境建立、喘息 | 中调、固定或慢横移、广中景 |
| `suspicion` | 怀疑/紧绷 | 试探、窥视、不对劲 | 中高反差、静态/微推、中近景 |
| `oppression` | 压迫 | 权力压制、无路可退 | 低调、略低机位、慢推 |
| `revelation` | 揭示 | 发现真相、信息落地 | 推近/变焦揭示/插入特写 |
| `intimacy` | 亲密 | 坦白、靠近、私密 | 柔光、浅景深、少运镜 |
| `grief` | 悲伤 | 失落、哀悼 | 去饱和、留白、长停顿 |
| `dread` | 恐惧/惊悚 | 危险、失衡 | 低调高反差、缓近、慎用荷兰角 |

### 别名（仅输入归一，不输出）

人写「背叛震惊」→ 归一为 `revelation` 或 `oppression`（看 beat）  
人写「不安」→ `suspicion` 或 `dread`  
完整别名表见 AI：`emotion_keys.json → aliases`

---

## 3. 交接合同（谁写什么）

| 从 → 到 | 必须交接的内容 | 禁止下一岗再发明 |
|---------|----------------|------------------|
| 剧作 → 对白 | 人物声口、场功能、情绪弧 | 新剧情事实 |
| 对白 → 导演 | 定稿台词、function、subtext | 改主题 |
| 导演 → 影调/摄影 | shot 列表、景别、beat、emotion | 改台词 |
| 影调 → 摄影 | film_look、scene_look、forbidden | 改分镜结构 |
| 摄影 → 时长 | camera.movement、镜头意图 | 改剧情 |
| 时长 → 编译 | duration、clips≤15/30 | 改运镜艺术决策 |
| 资产 ↔ 全员 | asset_id（可晚到） | 锁死某张图路径为唯一真相 |
| 编译 → 质检 | generation_jobs 提示词 | 质检不直接改艺术字段 |

---

## 4. 协作检查清单（人审）

- [ ] 本场 `emotion` 是否都在 7 key 内  
- [ ] 导演 shot 是否都有 `dramatic_beat` + `emotion.primary`  
- [ ] 摄影每镜是否有 `movement.motivation` 与 `look.motivation`  
- [ ] 时长是否 ≤ 用户选的 15/30  
- [ ] 最终提示词是否只组装、不发明新情节  

---

## 5. 维护流程

```text
1. 在 human/ 改理念与例子
2. 在 ai/ 改枚举与映射
3. python scripts/validate_knowledge_dual.py
4. 再跑 film-pipeline run 验证
```
