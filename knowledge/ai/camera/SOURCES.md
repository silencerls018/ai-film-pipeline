# 摄影知识库教学来源（工程化摘要）

本目录内容是对**常见影视教学与工业实践**的压缩，供 Agent 执行，**不是**抄录整门付费课程全文。

## 公开参考（可检索）

### 运镜动机与何时动

- **M. David Mullen, ASC** — *Notes on Camera Movement: When to Move the Camera and Why*  
  （StudentFilmmakers / 行业笔记：戏剧动机、动作跟随、立体感三理由）
- Film-school primers — **motivated vs unmotivated** camera movement

### 运镜类型与叙事用途

- **StudioBinder** — *Definitive Guide to Every Type of Camera Movement in Film*
- 本仓库词库 — `knowledge/camera/moves_catalog.json`（158 条，Excel 维护）

### 景别 / 角度 / 焦段

- **Adobe** / 标准 film language — camera shots, angles, focal length basics
- 常见 Cinematography 101 课纲 — wide / medium / close-up families

### 构图与取景

- **StudioBinder** — *Rules of Shot Composition in Film*（三分、对称、视线空间、引导线等）
- DP masterclass 语言 — 有意的居中 vs 三分、前景框景、负空间

### 覆盖镜头（Coverage）

- 剧情片 coverage 教学 — master → OTS → singles → insert；180° 轴线
- 经典对话覆盖模板（电影学院基础）

### 布光

- **StudioBinder** — Three-point lighting（key / fill / back）
- Film Lighting 101 — key-fill-back + **motivated practicals**（窗、台灯、霓虹故事内光源）
- 行业共识：三点光是脚手架；实战以**动机光**为主

### 工业课纲（概念层，不抄录）

- ASC Master Class 课纲主题 — lighting & camera setups, workflow（仅作主题边界参考）
- Udemy / 公开 videography masterclass 课纲中的 framing + high/low key 条目（概念对齐）

## 核心观念 → 工程文件

| 主题 | 代表来源类型 | 工程化进了哪 |
|------|----------------|--------------|
| 运镜必须有动机；何时动比怎么动更重要 | ASC 笔记、电影学院动机运镜课 | `motivation_types.json` |
| 运镜类型与叙事用途 | StudioBinder 等运镜指南 | `moves_catalog.json`（158）+ 策略过滤 |
| 景别 / 角度 / 焦段 | Adobe / 基础 film language | `angles_lenses_lighting_basics.json` |
| 构图取景 | StudioBinder composition | `composition_framing.json` |
| 覆盖镜头 | 剧情片 coverage 教学 | `coverage_moves.json` |
| 情绪 × 景别 × 主体 | 综合 + 导演三位一体 | `strategy_matrix.json` |
| 三点光 / 动机光 | StudioBinder + Lighting 101 | `three_point_and_motivated_light.json` |
| 情绪灯光 | 电影照明基础 | `look/lighting_for_emotion.json` |
| 决策顺序 | 本项目落地 | `decision_rules.json` |

## 使用原则

1. **教学概念 → 规则表**，不把整段网文塞进 prompt。  
2. 词库 158 条是「词典」；策略表是「何时用哪一类」。  
3. 更新词库用 Excel 导入；更新策略改 `strategy_matrix.json` / `motivation_types.json`。  
4. **摄影智能体**按 `decision_rules.json` 顺序读策略表再从 catalog 选题；代码 stub 仅供 CLI 无模型时的骨架演示，不是创作主路径。

## 免责

摘要自公开教育内容与行业通用术语，用于内部 AI 电影管线；**不构成**对任何付费课程（MasterClass、付费网课等）的再分发或替代。
