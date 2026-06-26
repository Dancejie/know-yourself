---
name: know-yourself
version: "2.3.0"
description: >
  基于用户与 OpenClaw 的全量聊天记录，分析行为指纹、认知风格、决策模式与核心动机，生成
  机密情报档案风格（FBI/KGB）的 HTML 传播页，包含：数据驱动的个性化文本、涂黑解密交互、
  框选自定义涂黑、阅后即焚倒计时（5分钟版/24小时版）、服务端真实销毁。
  同步输出 Redoc 在线文档；首次调用全量建档，之后每日 19:00 自动增量更新 + 工作日 10:00 早安鼓舞。
  内置 RPG 战斗系统：6职业（骑士/魔法师/战士/盗贼/圣骑士/术士）× 4怪物（史莱姆/哥布林/巨魔/龙），
  根据 character_stats.json 属性自动推荐职业，技能名称引用用户真实称号，Boss HP 随未完成任务数动态增强。
  触发词：「分析我」「生成我的档案」「know yourself」「了解我自己」「密档」「我的行为分析」「打一场」「战斗」。
requires:
  bins: [jq, python3, bun]
  python: [matplotlib, pillow, numpy]
  skills: [session-logs, hi-redoc-curd]
---

# Know Yourself — 德尔斐计划

## 核心框架

- **柏拉图灵魂三分**：理性（Logos）/ 激情（Thumos）/ 欲望（Epithumia）
- **社会工程学行为建模**：所有结论有数据支撑，注明来源与置信度
- **可视化**：4张图表（环形话题分布、雷达灵魂三分、条形能力评分、词频关键词）

---

## RPG 成长体系设计原则

> ⚠️ **核心约束：所有 RPG 元素必须从用户数据中生成，不存在模板或固有内容。**

### 必须个性化生成的内容

| 元素 | 生成依据 | 禁止 |
|------|---------|------|
| **职业（class）** | 用户的主要工作领域、技能组合、自我定位描述 | 使用通用职业名称（如「程序员」「分析师」） |
| **原型（archetype）** | 行为模式、决策风格、灵魂三分比例综合推断 | 套用预设原型列表 |
| **属性维度（6-8个）** | 用户话题分布、高频关键词、能力评分、交互风格中真实体现的能力面向 | 使用固定维度列表 |
| **属性数值** | 从行为数据推导，有据可查，不能拍脑袋 | 随意赋值或平均分配 |
| **称号** | 由真实的具体行为或成就触发，描述必须还原触发事件 | 预设称号库或通用奖励 |
| **转职路线** | 基于当前能力短板和用户自述的发展方向 | 通用职业晋升路径 |

### 首次建档时的 RPG 初始化流程

首次全量建档（Step 8 之后）执行以下步骤，生成 `memory/character_stats.json`：

**1. 读取数据**
```python
stats = json.load(open("/tmp/know_yourself_stats.json"))
# 获取：topics, question_style, top_keywords, soul_scores, capability_scores, date_range
```

**2. LLM 推断职业与原型**（由主 agent 生成，不调脚本）
- 根据 top_keywords + topics + 用户自述职位/背景，生成一个**独特的职业头衔**（不超过8字）
- 根据灵魂三分比例 + 行为模式，生成一个**英文原型名 + 中文副标题**

**3. LLM 生成 6-8 个个性化属性维度**
- 每个维度对应用户数据中真实可观测的能力面向
- 数值从 `capability_scores` 和行为频率推导，范围 1-100
- 每个维度有简短说明（15字内），说明数据来源

**4. LLM 生成初始称号（0-2个）**
- 只在有明确数据支撑的成就时给予
- 没有突出成就则留空，后续由每日更新逐步解锁

**5. LLM 生成周常成长目标（growth_goals）**

> ⚠️ **这是周常任务的唯一来源，不得硬编码，必须基于用户真实背景生成**

从以下渠道读取用户成长方向：
- `USER.md` 的「核心关切」章节
- Redoc 人物面板文档（若已存在）中的转职路线 / 长期目标描述
- session 中用户自述的长期目标（「我想做到…」「我需要提升…」「我的目标是…」）

生成 3-5 个个性化周常目标，格式：
```json
{
  "growth_goals": [
    {
      "id": "unique_snake_case_id",
      "name": "目标名称（4-8字，传神，不要过于通用）",
      "desc": "本周要完成的一句话说明（具体可执行）",
      "weekly_target": "本周完成X次/1篇/1条……（明确可验证）",
      "keywords": ["触发词1", "触发词2", "..."],   // 用于晚间自动识别完成
      "exp": 1000,
      "rarity": "epic",
      "source": "来源说明（如：USER.md 核心关切 / Redoc 转职路线 / 用户自述）"
    }
  ]
}
```

约束：
- 每个目标必须来自用户真实数据，不得拼凑通用目标
- `keywords` 至少5个，覆盖该目标的自然语言表达方式
- 不同目标之间互相独立，覆盖不同成长维度（避免两个投资、两个写作）

**6. 写入 character_stats.json**
```bash
# 直接由主 agent 构造 JSON 并写入，不使用预设模板
# growth_goals 字段与 profile/attributes/titles 平级
```

### 每日增量更新时的经验生成

晚间 Cron 生成经验事件时：
- **必须**基于当日真实会话内容，描述具体行为
- **禁止**生成「完成了今天的工作」这类无内容的泛化描述
- 称号触发条件必须在描述中体现，让用户看到触发原因
- 属性加成要与事件内容对应（写代码 → execution 加成，创意提案 → creativity 加成）

### 早安鼓舞的禁止清单

早安鼓舞「今日鼓励」模块的约束（防止模板套话）：
- **禁止词**：「负责到底」「修复到底」「认真负责」「坚持到底」「工程师精神」等通用套话
- **禁止行为**：编造不存在的事件、泛化成「完成了今天的工作」
- **必须**：引用 `character_history.txt` 里的具体事件原文
- **角度要有新意**：欣赏某个决策方式、认可某个思维模式、发现某个有意思的行为侧面
- **语气**：像真正了解这个人的朋友，不是 HR 写的表扬信

---

## 署名分析维度（重要信号）

用户在 Hi / 小红书等平台上的**薯名/署名**是高价值的自我投射信号，反映其认同的角色、价值观与世界观。建档时必须获取并深度解读。

### 获取方式

```bash
# 获取当前用户的 Hi 署名（薯名/redName）
bunx @xhs/hi-cli@0.2.15 search:employee \
  --query "$(bunx @xhs/hi-cli@0.2.15 search:me | python3 -c \
    "import sys,json; print(json.load(sys.stdin)['xhsContactId'])")" \
  2>/dev/null | python3 -c "
import sys, json
items = json.load(sys.stdin).get('items', [])
if items:
    u = items[0]
    print('姓名:', u.get('userName',''))
    print('薯名:', u.get('redName',''))
    print('部门:', u.get('departmentNamePath',''))
"
```

### 解读方法

> ⚠️ **核心原则：先画像，后参照。不能先对号入座，再用署名倒推结论。**
> 署名只是参考信号之一——用户可能只是觉得好听、好看、向往，未必深度认同其内涵。
> 正确顺序：先完成行为数据分析，形成独立画像，再将署名作为佐证或对照引入，
> 寻找「印证/矛盾/无关」三种关系，而非强行拟合。

1. **先完成独立画像**：基于 session 数据（话题/风格/灵魂/高频词）形成结论，不受署名影响
2. **署名来源考证**：判断是否为虚构角色（动漫/游戏/文学）、历史人物、自造词、意象词等
3. **角色特质检索**：若为虚构角色，通过 `web_search` 搜索其性格特质、核心价值观、标志性行为
4. **三向对照**：
   - **印证**：署名特质与行为画像一致 → 可作为补充佐证，适度引用
   - **矛盾**：署名特质与行为数据相悖 → 值得在档案中点出，可能揭示理想自我与真实自我的落差
   - **无关**：用户只是觉得好听/好看 → 如实注明「署名参考意义有限」，不强行解读
5. **写入档案**：综合判断后，仅将有实质意义的署名洞察写入 `sec1`，无意义则略去

### 示例（用户薯名「桐人」）

- **来源**：《刀剑神域》主角，黑衣剑士，独行侠气质
- **核心特质**：极强责任感、不惜代价保护他人、在虚拟与现实间构建双重身份、孤独但不孤立
- **投射信号**：选择「独行者」而非「领袖者」原型，认同的是「能力卓越但不依赖集体」的角色定位
- **交叉验证**：与 Logos 75%（理性主导）、执行型 26.8%（行动导向）、情感型 18.8%（有温度但克制）高度吻合

---

## 三种运行模式

| 模式 | 触发方式 | 说明 |
|------|---------|------|
| **全量建档** | 用户说「分析我」/ 「生成档案」| 首次执行，扫描全部会话 |
| **增量更新** | 每日 19:00 自动 Cron | 只扫描上次之后的新会话，更新档案并发晚间总结 |
| **早安鼓舞** | 工作日 10:00 自动 Cron | 读取最新档案状态，发温暖早安 |

---

## Step 1：判断模式

```bash
STATE=~/.openclaw/workspace/memory/know-yourself-state.json
if [ -f "$STATE" ]; then
  MODE="incremental"
  LAST_TS=$(jq -r '.last_analyzed' "$STATE")
  echo "增量模式：上次分析到 $LAST_TS"
else
  MODE="full"
  echo "首次全量建档"
fi
```

---

## Step 2：采集会话统计数据

```bash
SESSIONS_DIR=~/.openclaw/agents/main/sessions

# 全量模式：分析全部会话
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/extract_session_stats.py \
  "$SESSIONS_DIR" \
  --output /tmp/know_yourself_stats.json

# 增量模式：只分析 LAST_TS 之后的新会话
SINCE=$(python3 -c "from datetime import datetime,timezone; \
  print(datetime.fromisoformat('$LAST_TS'.replace('Z','+00:00')).timestamp())")
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/extract_session_stats.py \
  "$SESSIONS_DIR" \
  --since "$SINCE" \
  --output /tmp/know_yourself_stats.json
```

输出：`/tmp/know_yourself_stats.json`

> ⚠️ **soul_scores** 和 **capability_scores** 为主观评估基准值，脚本会输出默认值，
> 如需更新请在生成后手动编辑 stats.json 对应字段，再继续后续步骤。

### Step 2b：提取今日用户真实对话内容（晚间 Cron 专用）

> ⚠️ **这是晚间洞察的唯一可信数据来源。** `extract_session_stats.py` 只做频率统计，
> 无法区分今日具体发生了什么——必须用下面的脚本读取真实对话文本。

```bash
# 提取今日用户真实发言（过滤 cron payload / 系统 flush / metadata 头）
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/extract_today_messages.py \
  --date $(date +%Y-%m-%d) \
  --output /tmp/today_messages.txt

# 早安 Cron 读昨日内容：
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/extract_today_messages.py \
  --date $(date -d 'yesterday' +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d) \
  --output /tmp/yesterday_messages.txt
```

输出：`/tmp/today_messages.txt`（今日真实用户发言列表，已去除 cron / 系统消息）

**约束（晚间经验事件生成）：**
- 每条 `events[].desc` 必须引用 `/tmp/today_messages.txt` 中的具体事件
- 禁止生成「今日活跃交互」「系统巡航」「AI探索」等泛化描述
- 今日对话为空时，`events` 传空数组 `[]`

---

## Step 3：生成可视化图表

```bash
# 获取企业微信头像（首次或头像失效时）
bunx @xhs/hi-workspace-cli@0.2.12 search:employee \
  --query "$(bunx @xhs/hi-workspace-cli@0.2.12 search:me | \
    python3 -c "import sys,json;print(json.load(sys.stdin)['xhsContactId'])")" \
  2>/dev/null | python3 -c "
import sys,json
items=json.load(sys.stdin).get('items',[])
if items: print(items[0]['avatarUrl'])
" > /tmp/avatar_raw_url.txt

# 生成4张图表 + 头像
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/gen_charts.py \
  --stats /tmp/know_yourself_stats.json \
  --output-dir /tmp/know_yourself_charts \
  --username "$(jq -r '.name' ~/.openclaw/workspace/USER.md 2>/dev/null || echo '用户')"
```

输出目录：`/tmp/know_yourself_charts/`（topic_pie / soul_radar / score_bar / keyword_freq / avatar_square）

---

## Step 4：上传图表到 Redoc CDN

```bash
cd ~/.openclaw/workspace/skills/redoc-enhanced

for name in topic_pie soul_radar score_bar keyword_freq avatar_square; do
  CDN=$(./run.sh upload-file --file /tmp/know_yourself_charts/${name}.png 2>&1 \
        | grep "CDN:" | sed 's/.*CDN: //')
  eval "CDN_${name}=$CDN"
  echo "${name}: $CDN"
done
```

---

## Step 5：写入 / 更新 Redoc 文档

### 5a. 首次建档：创建新文档

> 首次建档时同步生成初始 history 记录：
> ```bash
> python3 skills/know-yourself/scripts/update_character_stats.py \
>   --char memory/character_stats.json \
>   --date $(date +%Y-%m-%d) \
>   --save-history
> ```
> 写入 `skills/know-yourself/references/character_history.txt`，记录初始等级/称号。

文档标题：`【德尔斐计划】[用户名]人物档案 v1.0`

文档结构（8节）：一、基础信息 → 二、证据条目 → 三、灵魂三分雷达 →
四、处世模式 → 五、认知盲区预警 → 六、模型评分 → 七、近期成长建议 → 八、AI 交互偏好手册

```bash
cd ~/.openclaw/workspace/skills/redoc-enhanced
DOC_ID=$(./run.sh create-doc --title "【德尔斐计划】[用户名]人物档案 v1.0" \
  --space-id "$SPACE_ID" --format json | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print(d['shortcutId'])")
./run.sh write-doc "$DOC_ID" --file /tmp/know_yourself_doc.md
```

### 5b. 增量更新：局部刷新文字 + 更新图表

```bash
PREV_CONTENT=/tmp/persona_content_prev.json
DELTA=/tmp/persona_content_delta.json

# 复制上次 content 作为基础（首次可跳过）
[ -f /tmp/persona_content.json ] && cp /tmp/persona_content.json "$PREV_CONTENT"

# 检测变化，生成增量段落
python3 ~/.openclaw/workspace/skills/know-yourself/scripts/gen_incremental_content.py \
  --stats-new    /tmp/know_yourself_stats.json \
  --stats-old    /tmp/know_yourself_stats_prev.json \
  --content-prev "$PREV_CONTENT" \
  --output       "$DELTA"

# 读取更新摘要（晚间通知使用）
SUMMARY=$(python3 -c "import json; print(json.load(open('$DELTA'))['_summary'])")
NEW_SESSIONS=$(python3 -c "import json; print(json.load(open('$DELTA'))['_new_sessions'])")

# 若有变化：用 delta 合并到旧 content，重新生成 HTML；无变化则跳过
CHANGED=$(python3 -c "import json; print(len(json.load(open('$DELTA'))['_changed_keys']))")
if [ "$CHANGED" -gt 0 ]; then
  echo "检测到 $CHANGED 个段落变化，重新生成 HTML..."
  python3 ~/.openclaw/workspace/skills/know-yourself/scripts/build_personalized.py 24h \
    --content       "$PREV_CONTENT" \
    --content-delta "$DELTA" \
    --user /tmp/know_yourself_user.json \
    --charts /tmp/know_yourself_charts
  cp /tmp/persona-dangsi-24h.html ~/.openclaw/workspace/public/persona-dangsi.html
else
  echo "无显著变化，跳过 HTML 重生成"
fi
```

---

## Step 6：生成 HTML 密档

详见 → [`references/html-spec.md`](references/html-spec.md)

关键步骤：
1. **主 agent** 读取 stats.json + USER.md，生成七段叙事内容，写入 `/tmp/persona_content.json`
   - content JSON 格式：[`references/content-json-spec.md`](references/content-json-spec.md)
2. 调用脚本生成两版 HTML（5min + 24h）
3. 验证通过后复制到 `public/` 部署
4. 确认 fileserver.py 在 8899 端口运行（参见 html-spec.md 启动方式）
5. 设置 24h 自动销毁 Cron

```bash
# 生成（--charts 注入4张 PNG 图表，--content-delta 用于增量更新）
python3 skills/know-yourself/scripts/build_personalized.py 5min \
  --content /tmp/persona_content.json \
  --charts  /tmp/know_yourself_charts

python3 skills/know-yourself/scripts/build_personalized.py 24h \
  --content /tmp/persona_content.json \
  --charts  /tmp/know_yourself_charts

# 验证
python3 skills/know-yourself/scripts/verify_html.py /tmp/persona-dangsi-5min.html

# 部署
cp /tmp/persona-dangsi-5min.html public/persona-dangsi-5min.html
cp /tmp/persona-dangsi-24h.html  public/persona-dangsi.html
```

---

## Step 7：更新状态文件

```bash
python3 << 'EOF'
import json, os, datetime

state_path = os.path.expanduser("~/.openclaw/workspace/memory/know-yourself-state.json")
state = {
    "doc_id":        os.environ.get("DOC_ID", ""),
    "last_analyzed": datetime.datetime.now().isoformat(),
    "session_count": int(os.environ.get("SESSION_COUNT", "0")),
    "charts": {
        "topic_pie":    os.environ.get("CDN_topic_pie", ""),
        "soul_radar":   os.environ.get("CDN_soul_radar", ""),
        "score_bar":    os.environ.get("CDN_score_bar", ""),
        "keyword_freq": os.environ.get("CDN_keyword_freq", ""),
        "avatar":       os.environ.get("CDN_avatar_square", ""),
    },
    "avatar_url": open("/tmp/avatar_raw_url.txt").read().strip()
               if os.path.exists("/tmp/avatar_raw_url.txt") else "",
}
with open(state_path, "w") as f:
    json.dump(state, f, ensure_ascii=False, indent=2)
print(f"状态已更新：{state_path}")
EOF
```

---

## Step 8：设置定时 Cron（首次建档后执行一次）

### 8a. 每日 19:00 晚间总结

```
cron 设置：
- name: "know-yourself 每日档案更新"
- schedule: cron "0 19 * * *" Asia/Shanghai
- sessionTarget: isolated
- timeoutSeconds: 500
- delivery: announce，channel: hi，to: 用户邮箱
- payload: agentTurn，消息：
  ⚠️ 不要调用 message 工具。直接输出晚间总结，系统自动投递。

  Step 1：增量数据采集（SKILL.md Step 1-2）
  Step 2：生成经验事件并更新人物面板：
    cd ~/.openclaw/workspace
    python3 skills/know-yourself/scripts/update_character_stats.py \
      --char memory/character_stats.json \
      --date $(date +%Y-%m-%d) \
      --save-history \
      --events-json '{"events": [{"desc": "具体行为", "exp": 数值, "attr_bonus": {"属性key": 增量}}]}'
    注意：events 必须基于今日真实交互，禁止泛化描述。
  Step 3：整体替换 Redoc 人物面板（防重复）：
    python3 skills/know-yourself/scripts/update_character_stats.py \
      --char memory/character_stats.json \
      --update-redoc 9582099871592449176c9d50b3ddadb9
    说明：此命令用 --format source 读取旧面板块并整体替换，
          img 标签用 source 模式写入（防止被 text 模式过滤），
          Redoc 自动补的 height 会被二次 patch 为正确比例值。
  Step 4：增量叙事刷新（SKILL.md Step 5b）
  Step 5：输出晚间总结：
    1. 📊 今日数据概况
    2. 🎮 今日成长记录（引用具体经验事件，像游戏日志）
    3. 🔍 今日新增洞察
    4. 🌟 今日闪光点（具体真实，禁止套话）
    5. 🌙 晚安寄语
  无新数据时说「档案在安静积累中」。
```

### 8b. 每日 09:00 早安 + 任务面板

早安消息 = 原有早安鼓舞 + 今日任务面板（叠加，不替代）。

```
cron 设置：
- name: "每日任务晨报"
- schedule: cron "0 9 * * *" Asia/Shanghai
- sessionTarget: isolated
- delivery: mode none（脚本内部通过 message 工具发送）
- payload: agentTurn，消息：

  ⚠️ 重要：不要调用 message 工具。

  执行早安消息生成流程：

  1. 运行：`cd /home/node/.openclaw/workspace && python3 skills/know-yourself/scripts/gen_daily_quest.py`
     读取 /tmp/daily_quest_morning_msg.txt 获取任务面板内容

  2. 读取 memory/character_stats.json 获取人物状态

  3. 提取昨日真实对话内容：
     ```
     python3 skills/know-yourself/scripts/extract_today_messages.py \
       --date $(date -d 'yesterday' +%Y-%m-%d 2>/dev/null || date -v-1d +%Y-%m-%d) \
       --output /tmp/yesterday_messages.txt
     ```
     读取 /tmp/yesterday_messages.txt，「昨日档案速览」必须基于此内容撰写，禁止泛化。

  4. 组织完整早安消息，风格要求：简洁温暖，不堵不水，整体不超过示例长度。结构如下：

  ☀️ 早安，明公！

  📋 昨日档案速览
  （1-2句话，有具体细节，不水账）

  🌟 今日鼓励
  （结合人物档案数据写有洞察的鼓励，必须具体，不泛泛而谈，禁止套话）

  🔭 长期坐标
  （1句，结合转职路线进度，点到为止）

  ――

  📋 今日任务
  （任务名称 + 1句话内容 + 完成方式 + 奖励一行，简洁不展开）

  🎖 本周周常
  （两个周常任务名称 + 进度 + 一句话提示，不展开）

  🦉

  5. 用 message 工具发送到 hi 频道，target 为用户邮箱，channel 为 hi
  只发一条 hi 消息，不要回复主会话。
```

**早安禁止清单**（继承原有约束）：
- 禁止词：「负责到底」「修复到底」「认真负责」「坚持到底」「工程师精神」等通用套话
- 禁止编造不存在的事件，必须引用 character_history.txt 或真实会话中的具体事件
- 今日鼓励要有角度：欣赏决策方式、认可思维模式、发现有趣行为侧面

---

### 8c. 每日 19:00 晚间档案 + 任务结算

晚间消息 = 原有晚间总结 + 任务结算（合并展示，不替代）。

```
cron 设置：
- name: "每日任务晚间结算"
- schedule: cron "0 19 * * *" Asia/Shanghai
- sessionTarget: isolated
- delivery: mode none（脚本内部通过 message 工具发送）
- payload: agentTurn，消息：

  ⚠️ 重要：不要调用 message 工具。

  执行晚间档案更新流程：

  1. 运行：`cd /home/node/.openclaw/workspace && python3 skills/know-yourself/scripts/settle_daily_quest.py`
     读取 /tmp/daily_quest_settle_msg.txt 获取结算数据（SETTLE_DATA）

  2. 读取 memory/character_stats.json 获取人物状态

  3. 提取今日真实对话内容：
     ```
     python3 skills/know-yourself/scripts/extract_today_messages.py \
       --date $(date +%Y-%m-%d) \
       --output /tmp/today_messages.txt
     ```
     读取 /tmp/today_messages.txt，⚠️ 经验事件和闪光点必须基于此真实内容，禁止靠高频词猜测。

  4. 组织完整晚间消息，结构如下：

  🌙 晚间档案更新报告 — {date}

  📊 今日数据概况
  （会话数、消息数、话题分布、关键词——简洁概述）

  🌟 明公今日闪光点
  （今日最有价值的一件事，详尽分析，这是核心——必须具体展开，不泛泛而谈）

  🎮 今日成长记录 + 任务完成情况
  （将 SETTLE_DATA 中的经验事件、任务完成情况、称号解锁内容合并展示，用表格呈现）

  🔍 新增洞察 + 隐藏任务线索
  （今天交互中的特别模式或反常行为——小心场景也可能触发隐藏称号）

  🌙 晚安
  （一两句，有温度，带称谓）

  5. 用 message 工具发送到 hi 频道，target 为用户邮箱，channel 为 hi
  只发一条 hi 消息，不要回复主会话。
```

---

## 输出规范

- 每条结论**必须注明数据来源**
- 置信度标注：High（直接观测）/ Medium（统计推断）/ Low（间接推断）
- 禁止无据猜测；不确定时标注「待验证」

## 数据安全

- 所有数据本地处理，不外传
- 用户可随时要求删除（删除 Redoc 文档 + state.json）

---

---

## Step 9：RPG 战斗系统（触发词：「打一场」「战斗」「开战」）

当用户说「打一场」「开打」「今日战斗」「去战场」「战斗系统」时，执行以下流程：

### 9a. 生成个性化战斗 HTML

```bash
python3 skills/know-yourself/scripts/gen_battle_interactive.py \
  --character-stats memory/character_stats.json \
  --daily-quest memory/daily_quest.json \
  --output public/battle_interactive.html
```

脚本自动完成：
- 读取 `character_stats.json`：属性权重计算 → 推荐最匹配职业（6选1）
- 读取 `daily_quest.json`：统计未完成任务数 → Boss HP 加成（×60/个）
- 技能个性化：用户持有的称号触发对应史诗/隐藏技能替换第4技能槽
  - 精密体系建筑师 → 🏛️ 架构降维打击（史诗·魔法，无视50%魔防）
  - 规则锻造者 → ⚖️ 边界锁定（史诗·物理，精准控制边界）
  - 工具建造者 → 🔧 工具链爆破（物理，批量输出）
  - Inspire Your Life → 💫 激情绽放（隐藏·魔法，全力以赴）

### 9b. 更新线上页面

```bash
cd skills/html-go-live && python3 scripts/html_go_live.py \
  --file public/battle_interactive.html \
  --name "德尔斐战斗系统" \
  --update 172A49CAC6F775415C41A0CE52BD2AC8 \
  --skip-maintainer-prompt
```

### 9c. 回复用户

回复格式：
```
✦ 战场已刷新！今日数据已同步：

🎮 **推荐职业**：{职业}（{推荐理由}）
⚔️ **怪物强度**：共 {N} 个未完成任务，Boss HP +{N×60}
🏆 **专属技能**：{从称号解锁的技能名}

👉 https://aifin.xiaohongshu.com/apps/copilot/chart-container?dashboardId=172A49CAC6F775415C41A0CE52BD2AC8
```

### 职业推荐逻辑（属性权重）

| 职业 | 核心属性 |
|------|---------|
| 骑士 | 执行纪律(40%) + 系统架构(30%) |
| 魔法师 | 框架思维(40%) + AI工程(35%) |
| 战士 | 执行纪律(45%) + 系统架构(30%) |
| 盗贼 | 产品审美(35%) + 文学表达(35%) |
| 圣骑士 | 共情力(40%) + 文学表达(20%) |
| 术士 | AI工程(40%) + 金融直觉(30%) |

---

## 文件结构

```
skills/know-yourself/
├── SKILL.md                          ← 本文件（执行流程主文档）
├── scripts/
│   ├── extract_session_stats.py      ← 会话统计（v2.0，支持 v3 JSONL）
│   ├── gen_charts.py                 ← 图表生成（v4.0，数据驱动）
│   ├── gen_rpg_radar.py              ← RPG 雷达图生成（深色档案风格）
│   ├── update_character_stats.py     ← 人物面板更新（经验/升级/Redoc同步）
│   ├── build_personalized.py         ← HTML 档案生成（框架+内容分离）
│   ├── gen_incremental_content.py    ← 增量叙事检测（5类变化阈值）
│   ├── verify_html.py                ← 生成后自动校验
│   ├── fileserver.py                 ← 文件服务（支持 /api/destruct）
│   ├── gen_daily_quest.py            ← 每日任务生成（09:00 早安 Cron 调用）
│   ├── settle_daily_quest.py         ← 每日任务结算（19:00 晚间 Cron 调用）
│   ├── gen_battle_interactive.py     ← 战斗系统 HTML 生成（个性化职业/技能/Boss）
│   ├── gen_battle_html.py            ← 战斗战报截图生成（Chrome headless）
│   ├── gen_battle_report.py          ← 战斗文字战报（PIL版，备用）
│   ├── generate_profile_text.py      ← 辅助（已弃用，主 agent 直接生成）
│   └── extract_today_messages.py     ← 从 JSONL 提取今日真实用户对话（过滤 cron/系统消息）
└── references/
    ├── archetype-system.md           ← 原型分类体系（v1.3）
    ├── content-json-spec.md          ← content JSON 格式 + 涂黑规范
    ├── html-spec.md                  ← HTML 密档功能、部署、fileserver
    ├── battle-system-design.md       ← 战斗系统设计文档（v0.2）
    ├── battle-interactive-template.html ← 战斗 HTML 模板（gen_battle_interactive.py 使用）
    ├── character_history.txt         ← 每日经验/称号历史记录（用户可下载清理后归档）
    ├── default_avatar.png            ← 内置默认头像
    ├── persona-template-html.html    ← HTML 参考存档
    ├── template-intel.md             ← Redoc 模式A：FBI/KGB 档案模板
    └── template-panel.md             ← Redoc 模式B：柏拉图人物面板模板

memory/（工作区根目录）
├── character_stats.json              ← 人物档案（等级/经验/属性/称号）
├── daily_quest.json                  ← 每日/周常任务状态（gen_daily_quest.py 维护）
└── know-yourself-state.json          ← 增量更新状态
```

### update_character_stats.py 参数说明

```bash
python3 skills/know-yourself/scripts/update_character_stats.py \
  --char memory/character_stats.json \
  --date 2026-04-21 \
  --events-json '{"events": [...]}' \  # 注入当日经验事件
  --save-history \                      # 沉淀到 references/character_history.txt
  --update-redoc <shortcutId> \         # 整体替换 Redoc 面板（防重复，source模式）
  --print-panel                         # 打印 Markdown 面板（调试用）
```

### Redoc 图片写入规范

```
⚠️ Redoc 图片写入必须用 --old-source/--new-source 模式（source 模式保留 img 标签）
   text 模式会过滤 <img> 标签，Markdown ![]() 也会被过滤。

Redoc 会自动补 height=原始像素高 → update_character_stats.py 自动二次 patch：
  读取 public/rpg_radar.png 真实尺寸 → 按 width=860 计算正确比例高度 → 覆盖写入
```

---

## 版本历史

| 版本 | 变更 |
|------|------|
| v2.3.0 | **洞察数据来源修复**：新增 `extract_today_messages.py`，从 JSONL 直接读取 `type=message + role=user` 真实对话，过滤 cron payload / Pre-compaction flush / HEARTBEAT 等系统消息。晚间结算 Cron Step 2 改为调用此脚本，经验事件必须基于真实内容，禁止高频词猜测。早安晨报昨日速览同步改用此脚本。解决了洞察内容天天重复（总写「PE追问」「AI探索」）的 bug。 |
| v2.2.0 | **RPG 战斗系统**：新增 gen_battle_interactive.py + battle-interactive-template.html。6职业可选（骑士/魔法师/战士/盗贼/圣骑士/术士），职业根据 character_stats.json 属性权重自动推荐；4怪物（史莱姆→哥布林→巨魔→龙）配套专属场景背景；技能个性化：称号触发隐藏/史诗技能，职业描述引用用户真实类名；Boss HP = 基础值 + 未完成任务数×60（越懈怠越强）。线上地址：dashboardId=172A49CAC6F775415C41A0CE52BD2AC8。触发词：「打一场」「战斗」「开战」。 |
| v2.1.0 | **每日任务系统**：新增 gen_daily_quest.py + settle_daily_quest.py + memory/daily_quest.json。日常经验自动结算（+25/次交互）+ 每日专属任务（+200 EXP + 稀有称号）+ 周常任务（+1000 EXP + 史诗称号，基于成长目标）。早安消息升级为早安鼓舞 + 任务面板叠加结构（简洁不喧宾夺主）；晚间消息升级为档案总结 + 任务结算合并（闪光点核心 + 成长记录 + 洞察/隐藏线索 + 晚安）。Cron 从工作日 10:00 改为每日 09:00，晚间结算 19:00。 |
| v2.0.0 | **RPG 成长体系**：character_stats.json + gen_rpg_radar.py + update_character_stats.py。职业/属性维度/称号全部个性化生成，无模板。经验事件、称号解锁、历史沉淀（character_history.txt）。Redoc 人物面板：source 模式写入 img 标签 + 自动修正 height 为比例值。**早安鼓舞防套话**：禁止「负责到底/修复到底」等通用词，必须引用具体事件。晚间 Cron 超时 300s→500s。 |
| v1.7.0 | **SKILL.md 重构**：拆分为主流程 + 三个 references 文档。**extract_session_stats.py v2.0**：修复 v3 JSONL 解析。**gen_charts.py v4.0**：全面数据驱动。 |
| v1.6.0 | 双 Cron 体系：每日 19:00 晚间总结 + 工作日 10:00 早安鼓舞 |
| v1.5.1 | 正文结论涂黑规范：17处涂黑 + CLASSIFIED/SENSITIVE 双标记 |
| v1.5.0 | 框架+内容分离架构：七段内容由主 agent 实时生成 |
| v1.4.x | 核心优势生成重构（去硬编码）、数据驱动自动涂黑、深度个性化描述 |
| v1.3.0 | 头像体系重构（hi-workspace-cli）、原型体系动态组合 |
| v1.2.0 | HTML 传播档案全面升级（阅后即焚/印章/心理特征三层推理） |
| v1.1.0 | 全量/增量双模式、Cron 定时更新、Redoc 文档写入 |
| v1.0.0 | 初始版本 |
