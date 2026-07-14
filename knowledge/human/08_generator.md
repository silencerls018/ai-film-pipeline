# 08 · 提示词写手（Generator / Prompt Writer）· 人维护

> **Skill：** `skills/prompt_writer` · 阶段名仍为 `generator`

## 职责
把上游 **FilmBible 合同** 写成 **视频模型可直接投喂的自然语言**。  
**不**重新创作剧情；**不**发明合同没有的人/物/动作。

## 必须合并的上游
导演 beat/景别 · 摄影运镜 · 可见光色 · **本镜 linked_dialogue** · 时长/时间轴 · 可选主体图号

## 输出字段
- `actor_free_prompt` / `director_guided_prompt`（**英文成品**）  
- `actor_free_prompt_zh` / `director_guided_prompt_zh`（**中文成品**，同等可投喂）  
- `visual_prompt` / `motion_prompt` / `negative_prompt`  
- `duration_sec` ≤ 用户所选 15 或 30  
- `zh_director_summary` 给人看  

## 正文格式（四段）
1. 指定主体（`图1是××`）  
2. 摄影设备与参数 + 本段时长  
3. 故事线：时间轴分镜（`0-2秒，…`）；台词要能辨认说话人  
4. 音效：有源 SFX；无配乐、无字幕、无水印  

## 铁律
- **Spec 没有的情节、人物、道具，禁止写入。**  
- **禁止**投喂正文写流水线黑话（「自行切镜更流畅」「Look 岗」「同上」）。  
- **禁止**把整场对白塞进一镜；只写 `linked_dialogue`。  
- 电影最终时长写在 `prompt_board` 文末，不塞进每条投喂正文。  
