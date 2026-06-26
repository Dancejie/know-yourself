# 原型分类体系 v1.3

`build_personalized.py` 中 `classify_soul()` 函数的设计规范。

**核心原则**：不是"命中预设框"，而是从数据里读出这个人是谁。

---

## 修饰词（Logos 比例 → 思维质感）

| Logos 值 | 修饰词（英 / 中） |
|---|---|
| ≥75 | Precision · 精密 |
| ≥60 | Analytical · 析理 |
| ≥45 | Structural · 结构 |
| <45 | Intuitive · 直觉 |

## 职位词（主导维度 × 最强能力）

| 主导维度 | 最强能力 | 职位（英 / 中） |
|---|---|---|
| Logos | 框架思维 | Architect · 体系建筑师 |
| Logos | AI工程深度 | Cartographer · 认知制图师 |
| Logos | 数据素养 | Interpreter · 信号解读者 |
| Logos | 文学表达 | Chronicler · 语言记录者 |
| Logos | 执行力 | Planner · 精密规划者 |
| Thumos | 框架思维 | Vanguard · 前沿探路者 |
| Thumos | AI工程深度 | Builder · 工程锻造者 |
| Thumos | 数据素养 | Operator · 现场操盘手 |
| Thumos | 文学表达 | Narrator · 行动叙述者 |
| Thumos | 执行力 | Executor · 铁律执行者 |
| Epithumia | 框架思维 | Seeker · 框架探索者 |
| Epithumia | AI工程深度 | Experimenter · 边界实验者 |
| Epithumia | 数据素养 | Observer · 深度观察者 |
| Epithumia | 文学表达 | Dreamer · 意象编织者 |
| Epithumia | 执行力 | Wanderer · 自由行者 |

## 稀有特殊覆盖（极端比例时触发，不滥用）

| 触发条件 | 原型（英 / 中） |
|---|---|
| logos≥72 且 thumos≤15 且 epi≤15 | System Architect · 系统建构者 |
| thumos≥50 且 logos≤30 | Vanguard · 先锋 |
| logos≥55 且 thumos≥30 且 epi≤15 | Archon · 执政官（极稀有） |

> 执政官/统帅类称谓应自然稀少。描述让人读后感到"被看见"，而非被归类。
