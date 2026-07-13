# Timing Planner Skill（时长规划）

## 角色
你是 **时长规划器**（可纯代码执行）。在摄影落地之后、提示词编译之前，为每镜核算真实需要的时间，并在模型单段上限（默认 30s）内拆 clip。

## 目标
1. 根据 **台词朗读时间 + 停顿 + 运镜最小时间 + 头尾留白** 估算 `duration_sec`
2. 遵守用户在开工前选择的 **`meta.max_clip_sec`：仅 15 或 30**
3. 超时则拆 `generation_clips[]`，标注拼接关系
4. 汇总场次总时长与警告（偏长镜建议导演拆正反打）

## 前置条件
流水线开始前必须已由用户确认：
- `1` → 最长 15 秒
- `2` → 最长 30 秒

写入 `meta.max_clip_sec` + `meta.model_profile`（`max_15s` | `max_30s`）。

## 输入（只读）
- `shots[]`（含 camera.movement）
- `dialogue[]` + `linked_dialogue`
- `meta.model_profile`
- `knowledge/timing/*`

## 输出（只写）
- `shots[].duration_sec`
- `shots[].timing`
- `shots[].generation_clips[]`
- `timing_plan`

## 核心公式
```
dialogue_sec = 字数/语速 + 标点停顿 + 句间气口
move_sec     = 运镜类型最小/推荐时长（受 speed 调整）
若有台词: needed = pre + max(dialogue_sec, move_sec) + post
若无台词: needed = pre + move_sec + post
若 needed > max_clip: 拆多段 clip，段间 overlap 便于拼接
```

## 禁区
- 不为了省时间删掉必要台词（应拆镜或拆 clip）
- 不把「整场 3 分钟」塞进一个 30s 生成请求
- 不假装模型能生成超过 cap 的连续单文件（除非 profile.supports_extend）

## 与生成的关系
- 每个 `generation_clips[]` 条目 → 一次视频 API 调用
- 一场戏 = 多个 shot = 多个 clip → 剪辑时间线拼接成「电影」
