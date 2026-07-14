# 05 · 摄影（Cinematography）· 人维护

> **AI 同步：** `ai/camera/decision_rules.json` · 大词库在 `knowledge/camera/`（Excel 导入）  
> **人维护运镜大表：** `E:\AI\知识库\提示词\运镜Prompt精品库_清洗版.xlsx` → `python scripts/import_camera_xlsx.py`

## 职责
在导演分镜 + Look 之上，落地单镜：**焦段、角度、运镜、灯光执行、motivation**。

## 专业要点
1. **运镜必须有动机**（narrative motivation），禁止无动机炫技。  
2. **焦段语言**：24–35 空间/压力；40–50 对话自然；65–85 隔离/亲密。  
3. **角度**：仰/俯/眼平/荷兰角（荷兰角稀用且要动机）。  
4. **轴线与视线**：正反打保 180°，除非刻意混乱。  
5. **词库用法**：按情绪从精品库选 `prompt_en`，写入 `movement.prompt_en`。  
6. **景别 ≠ 运镜**：景别来自导演；你可微调但不推翻叙事覆盖。

## 决策顺序
```text
emotion + dramatic_beat
  → emotion_to_camera 候选
  → style_pack 过滤禁用
  → 选定运镜词条 + 焦段 + 角度
  → 写 motivation
  → 服从 look_bible，破调写 break_look_reason
```

## 与时长
慢推/复合运镜会抬高 `move_sec`；别在 15s 模型上堆「超慢史诗运镜」而不拆镜。  
