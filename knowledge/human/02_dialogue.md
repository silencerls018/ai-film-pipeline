# 02 · 对白（Dialogue）· 人维护

> **AI 同步：** `ai/dialogue/rules.json` · `ai/dialogue/line_functions.json`

## 职责
把说明性、扁平台词压成有**潜台词**与**节奏**的可表演对白。

## 专业要点
1. **潜台词（Subtext）**：说 A 指 B；电影潜台词常靠行为与沉默，不靠旁白解释。  
2. **一句一功能**：`advance | reveal | mislead | relationship | atmosphere | reaction`  
3. **删说明**：镜头已看见的，不要再讲一遍。  
4. **声口统一**：跟人物 `voice` 走。  
5. **气口**：`silence_beats` 是合法的「镜头」。  

## 禁忌
- 对白不要扛全部叙事（影像也要说故事）  
- 禁止改核心剧情事实  
- 禁止写运镜/焦段

## 与下游
导演用 `linked_dialogue` 挂台词；时长岗按字数估说话时间。  
