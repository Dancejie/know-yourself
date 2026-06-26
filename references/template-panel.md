# 模式 B：人物面板模板（柏拉图灵魂三分 × RPG 成长面板）

## 渲染规范

用表格+进度条（文字模拟）呈现核心数值，用有序列表呈现成长建议。强调**可成长性**：每个维度标注当前短板与提升方向。

---

# 【德尔斐计划】人物面板

```
档案编号：DLF-{YYYY}-{USER_ID}
生成日期：{DATE}
数据周期：近 {N} 天会话记录
```

---

## 一、灵魂三分雷达（核心画像）

```
        理性（Logos）
            △
           / \
          /   \
         /  ●  \      ● = 当前灵魂重心
        /       \
激情 ──────────── 欲望
（Thumos）    （Epithumia）
```

| 灵魂维度 | 占比 | 表现特征 |
|----------|------|----------|
| 🧠 理性（Logos） | {logos_pct}% | {logos_desc} |
| 🔥 激情（Thumos） | {thumos_pct}% | {thumos_desc} |
| 💎 欲望（Epithumia） | {epithumia_pct}% | {epithumia_desc} |

**灵魂代号**：`{soul_archetype}`（如：「理性执政官」/「激情探索者」/「平衡哲学家」）

---

## 二、行为指纹库（欲望层）

> 你做了什么——从聊天记录提取的硬数据

| 指纹类型 | 观测结论 | 置信度 |
|----------|----------|--------|
| ⏰ 时间指纹 | {time_pattern} | High |
| 🗺️ 话题指纹 | {topic_distribution} | High |
| ❓ 提问指纹 | {question_style} | Medium |
| 🔤 语言指纹 | {language_style} | Medium |
| ⚙️ 操作指纹 | {usage_pattern} | High |

---

## 三、情绪与动机图谱（激情层）

> 你为什么这么做——行为背后的驱动力

**核心动机排序**（从强到弱）：

1. 🎯 **{motivation_1}**：{motivation_1_desc}
2. 🏆 **{motivation_2}**：{motivation_2_desc}
3. 🔐 **{motivation_3}**：{motivation_3_desc}

**情绪模式**：
- 常态：{emotion_normal}
- 压力下：{emotion_stress}
- 获得感：{emotion_reward}

---

## 四、认知与决策模型（理性层）

> 你怎么思考——AI 优化交互的核心依据

**认知风格**：`{cognitive_style}`
- 信息获取：{info_intake}
- 处理深度：{processing_depth}
- 思维方式：{thinking_mode}

**决策风格**：`{decision_style}`
- 决策速度：{decision_speed}
- 风险偏好：{risk_preference}
- 信任基础：{trust_basis}

**策略一致性**：{consistency_observation}

---

## 五、认知盲区与成长指南（认识无知）

> 不是评判，而是帮你看见自己

### 当前盲区预警

| 盲区 | 表现 | 影响 |
|------|------|------|
| ⚠️ {blind_spot_1} | {bs1_symptom} | {bs1_impact} |
| ⚠️ {blind_spot_2} | {bs2_symptom} | {bs2_impact} |
| ⚠️ {blind_spot_3} | {bs3_symptom} | {bs3_impact} |

### 个性化成长建议

**近期可执行（本月）**：
- [ ] {action_1}
- [ ] {action_2}

**中期方向（3-6个月）**：
- {direction_1}
- {direction_2}

**长期课题（1年+）**：
- {longterm_1}

---

## 六、AI 交互优化手册（供 USER.md 更新）

```yaml
# 粘贴至 USER.md 的「与 AI 交互偏好」节

output_style: "{style}"          # 如：简洁结构化，优先表格和列表
answer_depth: "{depth}"          # 如：提供底层逻辑，不只给结论
tone: "{tone}"                   # 如：直接切题，省略客套
avoid:
  - "{avoid_1}"
  - "{avoid_2}"
best_engagement_time: "{time}"   # 如：22:00-01:00 为深度思考时段
```

---

## 七、成长轨迹（动态更新记录）

| 版本 | 日期 | 主要变化 |
|------|------|----------|
| v1.0 | {DATE} | 初始生成 |

---

```
下次更新建议：{next_update_date}
数据充分度：{data_sufficiency}/5（会话记录越多，分析越准确）
```
