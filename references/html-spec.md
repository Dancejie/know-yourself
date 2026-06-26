# HTML 密档规范 v1.6

`build_personalized.py` 生成的 HTML 档案的功能、架构与部署说明。

---

## 架构（框架+内容分离）

- **脚本负责**：HTML 框架、排版、倒计时、涂黑交互、数据驱动字段（图表/评分/原型名/灵魂合成句）
- **主 agent 负责**：七段叙事内容（Identity / Strengths / Obs1-3 / Strategic Trajectory / Analyst's Note），通过 `--content` JSON 传入
- 两者分离，框架稳定、内容每次独立生成

---

## 功能清单

| 功能 | 说明 |
|------|------|
| 原型大印章 | 首页右上角，英文+中文原型，红色双框歪斜，第一眼可见 |
| 倒计时条 | 40px 大字居中，5min/24h 两版文案，最后 1 分钟红色闪烁 |
| 工具栏 | 框选涂黑开关 / 撤销 / 保存为文件 |
| 预设涂黑 | `.R` class，点击解密，英中双语联动 |
| 框选自定义涂黑 | 拖选任意文字变黑，点击解密 |
| 立即销毁按钮 | 调用 `POST /api/destruct` 删除服务端文件 + 客户端销毁画面 |
| 倒计时归零 | 自动触发销毁流程 |
| 保存为文件 | 导出当前 HTML 快照（含涂黑状态） |

---

## 运行方式

```bash
# 1. 主 agent 写入 content JSON
# 写 /tmp/persona_content.json（见 content-json-spec.md）

# 2. 生成 HTML
python3 skills/know-yourself/scripts/build_personalized.py 5min \
  --content /tmp/persona_content.json

python3 skills/know-yourself/scripts/build_personalized.py 24h \
  --content /tmp/persona_content.json

# 3. 验证（必须全 ✅ 才发布）
python3 skills/know-yourself/scripts/verify_html.py /tmp/persona-dangsi-5min.html

# 4. 部署
cp /tmp/persona-dangsi-5min.html public/persona-dangsi-5min.html
cp /tmp/persona-dangsi-24h.html  public/persona-dangsi.html
```

输出文件：
- `/tmp/persona-[code]-5min.html`：5 分钟阅后即焚版
- `/tmp/persona-[code]-24h.html`：24 小时后自动销毁版

---

## 配套文件服务（fileserver.py）

需要一个支持 `POST /api/destruct` 的 Python HTTP 服务（非纯静态）。

**核心逻辑**：
- `POST /api/destruct` body: `{"file": "xxx.html", "token": "sha256前16位"}`
- token = `sha256(filename)[:16]`，验证通过则删除 `public/` 下对应文件
- token 基于文件名，服务重启后仍有效

**启动方式**：首次建档完成后自动在后台启动，监听 8899 端口：

```bash
nohup python3 ~/.openclaw/workspace/skills/know-yourself/scripts/fileserver.py \
  --port 8899 \
  --public-dir ~/.openclaw/workspace/public/ \
  > /tmp/fileserver.log 2>&1 &
echo $! > /tmp/fileserver.pid
echo "文件服务已启动 PID=$(cat /tmp/fileserver.pid)"
```

检查是否已运行：

```bash
curl -s http://localhost:8899/health || echo "未运行"
```

---

## 用户元信息配置

`build_personalized.py` 从 `/tmp/know_yourself_user.json` 读取（可通过 `--user` 覆盖）：

```json
{
  "name":           "代号/昵称",
  "real_name":      "真实姓名",
  "code":           "档案代码（大写字母）",
  "dob":            "YYYY-MM-DD",
  "age":            27,
  "affiliation_en": "Org · Dept (English)",
  "affiliation_zh": "机构 · 部门",
  "bg_en":          "Educational and career background",
  "bg_zh":          "教育和职业背景",
  "agent_name":     "Alice"
}
```

---

## 头像 Fallback 链

| 优先级 | 来源 |
|--------|------|
| 1 | `/tmp/avatar_raw_url.txt`（hi-workspace-cli 获取的企业微信头像 URL） |
| 2 | SSO 实时拉取（pod 内可能 404，备用） |
| 3 | `/tmp/avatar_b64.txt` base64 缓存 |
| 4 | `references/default_avatar.png` 内置默认 |
| 5 | 灰色占位符 |

获取企业微信头像（pod 内正确方式）：

```bash
bunx @xhs/hi-workspace-cli@0.2.12 search:employee \
  --query "$(bunx @xhs/hi-workspace-cli@0.2.12 search:me | python3 -c \
    "import sys,json;print(json.load(sys.stdin)['xhsContactId'])")" \
  2>/dev/null | python3 -c "
import sys, json
items = json.load(sys.stdin).get('items', [])
if items: print(items[0]['avatarUrl'])
" > /tmp/avatar_raw_url.txt
```

---

## 24 小时自动销毁 Cron

档案发布后自动设置服务端定时销毁：

```
cron 工具：
- schedule: at，24小时后 ISO 时间戳
- payload: agentTurn，消息：「执行密档自毁：删除 public/persona-xxx.html」
- deleteAfterRun: true
```

---

## 发布通知模板

```
密档已生成 ✅
- 24小时版：http://[IP]:8899/persona-[code].html
- 5分钟版（阅后即焚）：http://[IP]:8899/persona-[code]-5min.html
- 服务端定时销毁已设置（24小时后自动执行）
原型标签：[soul_name_zh] · [soul_name_en]
```
