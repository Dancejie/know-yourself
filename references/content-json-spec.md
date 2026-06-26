# content JSON 规范 v1.5.1

主 agent 生成后通过 `--content /tmp/persona_content.json` 传入 `build_personalized.py`。

---

## 字段结构

| Key | 章节 | 说明 |
|-----|------|------|
| `sec1_en` / `sec1_zh` | I. Identity | 背景轨迹叙事，不只是简历堆砌 |
| `sec2_intro_en` / `sec2_intro_zh` | II. Core Strengths intro | 数据方法论说明，措辞每次不同 |
| `obs1_en` / `obs1_zh` | III. Observation 1 | 交互结构推断（来源：style_distribution） |
| `obs2_en` / `obs2_zh` | III. Observation 2 | 认知负载特征（来源：avg_message_length + emoji_pct） |
| `obs3_en` / `obs3_zh` | III. Observation 3 | 峰值决策窗口（来源：peak_hours + top_keywords） |
| `sec6_en` / `sec6_zh` | VI. Strategic Trajectory | 职业向量推断，含跨域联结解读 |
| `sec7_en` / `sec7_zh` | VII. Analyst's Note | 主要制约因素根因分析 |
| `strengths` | II. Core Strengths | 列表，每项含 `id/en_title/zh_title/score/en_body/zh_body` |
| `vulns` | V. Cognitive Vulnerabilities | 列表，每项含 `id/en_title/zh_title/en_body/zh_body` |

**降级机制**：`--content` 未传入时，各章节回退到脚本内置数据驱动分支（保留兼容性）。

---

## 数据来源参照

生成各段内容时，从以下字段读取：

```
stats.json:
  session_count / total_messages / date_range
  question_style.style_distribution  → 分析型/执行型/情感型/创意型 %
  language_style.avg_message_length / emoji_usage_pct
  time_pattern.peak_hours / pattern_label
  top_keywords                        → 高频词列表
  topics.distribution                 → 各话题 pct + trend
  soul_scores                         → logos/thumos/epithumia %
  capability_scores                   → 能力 → 分数

USER.md:
  name / bg_en / bg_zh / affiliation_en / affiliation_zh
```

---

## 涂黑嵌入规范 v1.5.1

### 两层涂黑

**第一层（脚本自动）**：从数据推导，注入 meta-grid：
- 置信度 Low（sessions < 30 / 能力分平坦）→ `UNVERIFIED`
- 敏感认知盲区（emo < 8% / epi < 8%）→ `SENSITIVE`
- 极端异常值（cap ≥ 9.0 / 话题 > 55% / logos ≥ 78%）→ `CLASSIFIED`

**第二层（主 agent 在 content JSON 中嵌入）**：

```html
<span class='R' id='唯一ID' data-reveal='点击后显示的真实结论' data-tag='CLASSIFIED'>█████████████████</span>
```

### tag 选择

| tag | 颜色 | 适用场景 |
|-----|------|---------|
| `CLASSIFIED` | 红 | 核心能力判断、职业向量推断、认知风格定性 |
| `SENSITIVE` | 红+虚线 | 认知盲区根因、心理制约内部机制 |

### id 命名约定

| 前缀 | 位置 |
|------|------|
| `s1a / s1az` | Str-1 英/中 |
| `s2a~s4az` | Str-2 至 Str-4 |
| `vd1 / vd1z` | Vuln-1 英/中 |
| `ob1a / ob1az` | Obs-1 英/中 |
| `an1 / an1z` | 分析员备注 |

**密度参考**：每个 strengths/vulns 条目至少 1 处涂黑；核心结论必须涂黑，不留明文。
