# 模式 A：情报档案模板（FBI/克格勃风格）

## 渲染规范

使用代码块或等宽字体呈现档案头部，正文用 Markdown 表格和有序列表。

---

```
┌─────────────────────────────────────────────────────────────┐
│  机密等级：███  //  内部代号：PERSONA-OPS / Delphic Systems  │
│  档案编号：DS-PN-{YYYY}-{USER_ID}                           │
│  分发：行为建模组  分析员：Alice·V                           │
│  最后修订：{DATE}  版本：v1.0                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 一、基础信息

| 字段 | 值 | 来源 | 置信度 |
|------|----|------|--------|
| 代号 | `{display_name}` | USER.md | High |
| 年代群体 | `{cohort}` | USER.md | High |
| 灵魂代号 | `{soul_archetype}` | 建模推断 | Medium |
| 核心标签 | `{tag_1}` / `{tag_2}` / `{tag_3}` | 会话分析 | Medium |
| 危险等级 | ★★★★☆（成长潜力指数） | 综合评估 | Medium |

---

## 二、证据条目（Evidence Ledger）

> 每条结论注明来源与置信度

1. **时间指纹**：`{活跃时段}` 为高密度交互期（Source: SessionLogs / High）
2. **话题分布**：`{topic_1}` {pct_1}% / `{topic_2}` {pct_2}% / `{topic_3}` {pct_3}%（Source: SessionLogs / High）
3. **提问模式**：`{question_pattern}`（Source: SessionLogs / Medium）
4. **决策特征**：`{decision_trait}`（Source: 当前会话 / Medium）
5. **待验证**：`{unconfirmed_hypothesis}`（Source: 推断 / Low）

---

## 三、行为画像 & 决策风格（Narrative）

- **行动风格**：`{action_style}`
- **决策节奏**：`{decision_pace}`
- **情绪触点**：`{emotional_trigger}`
- **纪律性**：`{discipline_observation}`

---

## 四、脆弱点与成长关注（Ethics & Risk）

- **认知盲区**：`{blind_spot_1}`；`{blind_spot_2}`
- **行为风险**：`{behavioral_risk}`
- **成长摩擦点**：`{growth_friction}`

---

## 五、时间线（Timeline）

```
{DATE_1}：{event_1}
{DATE_2}：{event_2}
{DATE_3}：{event_3}
```

---

## 六、模型评分（1–5；5为最高）

| 维度 | 评分 | 说明 |
|------|------|------|
| 执行力（目标→行动） | {score}/5 | {note} |
| 认知深度 | {score}/5 | {note} |
| 策略一致性 | {score}/5 | {note} |
| 成长潜力 | {score}/5 | {note} |
| AI 协作流畅度 | {score}/5 | {note} |

---

## 七、假设与替代解释（Analytic Tradecraft）

- **假设 A**：`{hypothesis_a}`（Supporting evidence: `{evidence}`）
- **备选 B**：`{hypothesis_b}`（需进一步验证）

---

## 八、AI 交互优化建议

- **输出风格**：`{style_pref}`
- **回答深度**：`{depth_pref}`
- **禁忌**：`{avoid}`

---

```
[分析员手写批注]
"{analyst_note}" —— Alice·V {DATE}
```
