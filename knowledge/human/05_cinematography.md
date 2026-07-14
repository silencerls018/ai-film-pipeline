# 05 · 摄影（Cinematography）· 人维护 / 教学版

> **AI 同步：**  
> `ai/camera/decision_rules.json`  
> `ai/camera/motivation_types.json`  
> `ai/camera/strategy_matrix.json`  
> `ai/camera/coverage_moves.json`  
> `ai/camera/angles_lenses_lighting_basics.json`  
> `ai/camera/composition_framing.json`  
> `ai/camera/three_point_and_motivated_light.json`  
> 词库：`knowledge/camera/moves_catalog.json`（158 条）  
> 来源说明：`ai/camera/SOURCES.md`

---

## 1. 摄影岗职责（本项目）

在导演分镜 + Look 之上，落地单镜：

- 焦段、角度、运镜 + **英文 catalog 句**
- 执行层灯光（动机光优先）
- **motivation 必须说清叙事原因**
- 构图用**可见画面事实**（居中 / 三分 / 过肩前景），少堆理论名词

### 本项目机位屋规（House style）

1. **除非非常必要，尽量不要用固定机位**  
   优先：缓推 / 微漂 / 横移 / 慢摇 / 爬行逼近 / 焦点转移。  
   固定仅用于：导演明确 lock、证件/监控平板、宏观 INSERT 一动就糊、brief 强制。

2. **就算固定，也不要默认纯平视**  
   机位要**带角度**：微俯 / 微仰 / 仰拍 / 俯拍 / 轻荷兰角 / 荷兰角等。  
   纯 `eye_level` 仅在「中性诚实」本身就是戏点时使用。

3. **荷兰角可用**（怀疑 / 压迫 / 恐惧或失序 beat），须写 motivation；仍禁用无动机 360 环绕 / crash zoom / whip。

---

## 2. 学院/工业核心课：运镜动机

**金句（工业共识）：**  
何时、为何动镜头，比「用什么设备动」更重要。

### ASC 三理由（M. David Mullen 笔记摘要）

| 理由 | 白话 |
|------|------|
| 戏剧/情绪 | 加压、贴近表情、孤立、释放 |
| 逻辑/动作 | 跟人走、跟重要动作，观众不迷路 |
| 立体感 | 轻微位移做出视差，让 2D 画面有真实纵深/落差 |

### 七种动机类型（简化课纲）

| 动机 | 白话 | 典型手段 |
|------|------|----------|
| 跟随动作 | 人在动，镜头跟着 | pan / track |
| 揭示信息 | 让观众看见新信息 | reveal pan / dolly past |
| 情绪强调 | 推进内心（不必跟人走） | slow push-in / dolly out |
| 空间定位 | 讲清房间/站位关系 | lateral / establishing |
| 主观沉浸 | 像角色的神经 | handheld / POV |
| 立体纵深 | 用视差做出 3D 感 | slow lateral past FG |
| 能量节奏 | 提速、冲击 | whip / crash（慎用） |

**固定机位也是策略**：权力、凝视、惊悚冷静、观察式纪录片感。

**无动机禁用（默认）：** 荷兰角、360 环绕炫技、crash zoom、whip pan。

---

## 3. 景别课（Shot size）

| 景别 | 叙事功能 |
|------|----------|
| EWS/WS | 建立空间、渺小、史诗 |
| FS/MS | 身体、站位、关系 |
| MCU/CU | 表演、反应、压力 |
| ECU/INSERT | 细节、信息、物证 |

教学要点：景别 = 主体占画面多少；**先定景别再定运镜**，不要反着来。

---

## 4. 角度与焦段课

| 角度 | 感觉 | 本项目优先级 |
|------|------|----------------|
| 微仰 slight_low | 略抬权力、肖像默认 | **高** |
| 仰 low_angle | 权力、压迫、崇高 | 压迫/揭示 |
| 微俯 slight_high | 观察、脆弱、桌面 INSERT | **高** |
| 俯 high_angle | 监视、渺小、压力 | 悲伤/恐惧/怀疑 |
| 轻荷兰 dutch_mild | 不安、紧绷 | 怀疑/恐惧 |
| 荷兰 dutch_angle | 失序 | 恐惧/压迫峰值 |
| 平视 eye_level | 中性诚实 | **最低（少用）** |

| 焦段 | 感觉 |
|------|------|
| 24–28 | 空间、略畸变、环境压人 |
| 35–40 | 对话万能、人在空间 |
| 50 | 偏自然 |
| 65–85 | 隔离、亲密、浅景深 |

完整表：`angles_lenses_lighting_basics.json` → `angle_by_emotion`。

---

## 5. 构图课（Composition）

公开教学常见条目（StudioBinder 等）：

| 手法 | 何时用 |
|------|--------|
| 三分法 | 默认平衡；近景眼睛靠上三分 |
| 居中强压 | 权力、对峙、仪式、孤立 |
| 视线/运动前方空间 | 有去向；反着用=被困 |
| 前景框景 | 门框/过肩/玻璃——纵深与窥视 |
| 负空间 | 孤独、恐惧、渺小 |
| 前景-中景-背景 | 电影感空间；可配合横移视差 |

写 prompt 时写**看得见的位置**，不要只写「使用三分法」。

完整表：`composition_framing.json`。

---

## 6. 覆盖镜头 + 运镜能量（Coverage）

经典对话覆盖（电影学院基础）：

```text
主镜头 WS 固定
→ OTS A / OTS B 固定（守轴线）
→ 单人 MCU（压力时可慢推）
→ 反应持镜
→ 必要 INSERT
```

| 覆盖角色 | 默认运镜能量 | 默认角度 |
|----------|----------------|----------|
| 建立/主镜头 | 慢摇 / 横移 | 微俯 / 俯 / 微仰 |
| 关系中景 | 微漂 / 横移 | 过肩微俯仰 |
| 表演近景 | 慢推 / 微漂 | 微仰 / 微俯 |
| 插入细节 | 轻推 / 微漂（**别写人脸微表情**） | 微俯 / 俯 |

---

## 7. 布光课：三点光脚手架 + 动机光

| 角色 | 工作 | 故事内可动机 |
|------|------|----------------|
| Key 主光 | 造型与主方向 | 窗、台灯、霓虹 |
| Fill 辅光 | 控阴影深浅 | 墙反、环境散射 |
| Back/Edge | 与背景分离 | 门口 spill、后窗 |
| Background | 空间层次 | 深处 practical |

**金句：** 三点光是入门脚手架；片场优先「戏里说得通的光」。  
情绪反差见 `three_point_and_motivated_light.json` + `lighting_for_emotion.json`。  
低调也要尽量**护眼可读**（除非戏要藏眼）。

---

## 8. 策略矩阵（本项目落地）

**情绪 × 景别 × 主体类型 → 允许的运镜族**

例：

- `revelation + CU + person` → 慢推 / 固定 / 拉镜孤立  
- `revelation + INSERT + object` → 固定 / 轻推 / 焦点转移（**不要选 sleeping figure 类句子**）  
- `intimacy + MCU + person` → 固定 / 微漂  
- `oppression + MCU + person` → 慢推 / 爬行逼近  

完整表见：`strategy_matrix.json`。  
**由摄影智能体**读表决策；词库只是候选句，不是自动替你选片。

---

## 9. 决策顺序（给摄影 Agent）

```text
1 读 emotion + beat + shot_size + subject
2 判断主体：人 / 物INSERT / 环境 / 双人
3 查 strategy_matrix 得到运镜族（运动优先，固定垫底）
4 在 158 词库里按关键词挑 prompt_en（且与主体不矛盾）
5 选非平视角度 + 匹配高度 + 焦段 + 构图可见事实
6 写简短叙事 motivation（禁止「因为知识库」）
7 灯光：动机光 + 情绪表 + look_bible
```

---

## 10. 与上下游

| 上游 | 给什么 |
|------|--------|
| 导演 | 景别、beat、emotion、表演意图、运镜倾向 |
| Look | 全片/场次影调禁区 |
| 词库 Excel | 158 条英文运镜句 |

| 下游 | 拿什么 |
|------|--------|
| 时长 | 运镜类型估秒数 |
| 提示词 | camera.movement.prompt_en + look |

---

## 11. 维护

- 改**策略**：改 `strategy_matrix.json` / `motivation_types.json`  
- 改**词典**：Excel → `python scripts/import_camera_xlsx.py`  
- 改**理念说明**：改本文，再同步 AI JSON 字段  
- 改**构图/布光课**：改 `composition_framing.json` / `three_point_and_motivated_light.json`

教学来源摘要见 `ai/camera/SOURCES.md`。
